#!/usr/bin/env python3
import argparse
import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import http.client
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse

from budget_download import BudgetReached, Downloader, Meter, RegistryBudgetReached

PROJECT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT / "sync/campaign-350gb.json"


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n")
    os.replace(temporary, path)


def safe_relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Unsafe repository path: {value}")
    return str(path)


class Campaign:
    def __init__(self, config):
        self.config = config
        self.root = Path(config["data_root"])
        self.state = self.root / "sync-state" / config["id"]
        self.meter = Meter(config, self.state)
        self.downloader = Downloader(self.meter)
        self.db = self.meter.db
        self.db.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, key TEXT UNIQUE, registry TEXT, kind TEXT, payload TEXT, status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0, next_try REAL DEFAULT 0, error TEXT DEFAULT '')")
        self.db.commit()
        sys.path.insert(0, str(self.root / "campaign-lib"))

    def enqueue(self, key, registry, kind, payload):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO jobs (key,registry,kind,payload) VALUES (?,?,?,?)", (key, registry, kind, json.dumps(payload)))

    def package(self, registry, name, spec=""):
        from packaging.utils import canonicalize_name
        if registry == "pypi":
            name = canonicalize_name(name)
        if not re.fullmatch(r"(?:@[a-zA-Z0-9_.-]+/)?[a-zA-Z0-9_.-]+", name):
            return
        count = self.db.execute("SELECT COUNT(*) FROM jobs WHERE registry=? AND kind='metadata'", (registry,)).fetchone()[0]
        if count < self.config["max_packages"]:
            self.enqueue(f"{registry}:{name}:{spec}", registry, "metadata", {"name": name, "spec": spec})

    def seed(self):
        for registry in ("pypi", "npm"):
            for line in (PROJECT / f"sync/lists/{registry}-top.txt").read_text().splitlines():
                if line.strip() and not line.startswith("#"):
                    self.package(registry, line.strip())
        for item in self.config["apt"]:
            self.enqueue(f"apt:{item['registry']}:{item['suite']}", item["registry"], "apt-index", item)

    def setup_django(self):
        sys.path.insert(0, str(PROJECT))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        os.environ.setdefault("DB_NAME", str(self.root / "database/db.sqlite3"))
        os.environ.setdefault("MIRROR_STORAGE_ROOT", str(self.root / "storage"))
        import django
        django.setup()

    def pypi_metadata(self, job):
        from packaging.requirements import InvalidRequirement, Requirement
        from packaging.specifiers import SpecifierSet
        from packaging.version import InvalidVersion, Version
        from packaging.utils import parse_wheel_filename
        name, spec = job["name"], job["spec"]
        document = self.downloader.json(f"https://pypi.org/pypi/{quote(name)}/json", "pypi")
        versions = []
        for raw, files in document["releases"].items():
            try:
                version = Version(raw)
                if not version.is_prerelease and not version.is_devrelease and files:
                    if not spec or version in SpecifierSet(spec):
                        versions.append((version, raw))
            except InvalidVersion:
                continue
        selected = sorted(versions, reverse=True)[:1 if spec else self.config["pypi_versions"]]
        for _, version in selected:
            release = self.downloader.json(f"https://pypi.org/pypi/{quote(name)}/{quote(version)}/json", "pypi")
            for requirement in release["info"].get("requires_dist") or []:
                try:
                    dependency = Requirement(requirement)
                    if dependency.url:
                        continue
                    self.package("pypi", dependency.name, str(dependency.specifier))
                except InvalidRequirement:
                    continue
            for item in document["releases"][version]:
                if item.get("yanked") or not item.get("digests", {}).get("sha256"):
                    continue
                filename = item["filename"]
                if filename.endswith(".whl"):
                    _, _, _, tags = parse_wheel_filename(filename)
                    if not any((tag.platform == "any" or (tag.platform.endswith("x86_64") and "linux" in tag.platform)) and (tag.interpreter.startswith("py") or tag.interpreter in {"cp310", "cp311", "cp312", "cp313", "cp314"} or tag.abi == "abi3") for tag in tags):
                        continue
                elif item.get("packagetype") != "sdist":
                    continue
                if urlparse(item["url"]).hostname != "files.pythonhosted.org" or not item["url"].startswith("https://"):
                    raise ValueError("Untrusted PyPI artifact URL")
                digest = item["digests"]["sha256"]
                self.enqueue(f"pypi-file:{name}:{version}:{filename}", "pypi", "pypi-file", {"name": name, "version": version, "filename": filename, "url": item["url"], "sha256": digest, "size": item["size"], "requires_python": item.get("requires_python") or ""})

    def pypi_file(self, job):
        from django.db import transaction
        from apps.artifacts.models import Artifact, Blob, Package, PackageVersion
        from apps.pypi_mirror.models import RemoteFile
        digest = job["sha256"]
        relative = f"{digest[:2]}/{digest[2:4]}/{digest}"
        target = self.root / "storage/blobs/sha256" / relative
        self.downloader.fetch(job["url"], target, "pypi", digest, size=job["size"])
        with transaction.atomic():
            package, _ = Package.objects.get_or_create(registry="pypi", normalized_name=job["name"], defaults={"display_name": job["name"]})
            version, _ = PackageVersion.objects.get_or_create(package=package, version=job["version"])
            blob, _ = Blob.objects.get_or_create(sha256=digest, defaults={"relative_path": relative, "size": target.stat().st_size})
            artifact, created = Artifact.objects.get_or_create(package_version=version, filename=job["filename"], defaults={"blob": blob, "upstream_url": job["url"], "expected_sha256": digest})
            if created:
                blob.reference_count += 1
                blob.save(update_fields=["reference_count"])
            RemoteFile.objects.update_or_create(package_version=version, filename=job["filename"], defaults={"url": job["url"], "sha256": digest, "requires_python": job["requires_python"], "artifact": artifact})

    def npm_metadata(self, job):
        from semantic_version import NpmSpec, Version
        name, spec = job["name"], job["spec"]
        if spec.startswith("npm:"):
            alias, _, constraint = spec[4:].rpartition("@")
            self.package("npm", alias or spec[4:], constraint if alias else "")
            return
        document = self.downloader.json(f"https://registry.npmjs.org/{quote(name, safe='')}", "npm")
        versions = []
        if spec in document.get("dist-tags", {}):
            spec = document["dist-tags"][spec]
        try:
            constraint = NpmSpec(spec or "*")
        except ValueError:
            print(f"UNSUPPORTED npm dependency: {name} {spec}", flush=True)
            return
        for raw in document.get("versions", {}):
            try:
                version = Version(raw)
                if not version.prerelease and constraint.match(version):
                    versions.append((version, raw))
            except ValueError:
                continue
        for _, version in sorted(versions, reverse=True)[:1 if spec else self.config["npm_versions"]]:
            item = document["versions"][version]
            dist = item.get("dist", {})
            integrity = dist.get("integrity", "")
            sha512 = next((value for value in integrity.split() if value.startswith("sha512-")), None)
            if not sha512:
                print(f"SKIP npm without SHA512: {name}@{version}", flush=True)
                continue
            if urlparse(dist["tarball"]).hostname != "registry.npmjs.org" or not dist["tarball"].startswith("https://"):
                raise ValueError("Untrusted npm artifact URL")
            self.enqueue(f"npm-file:{name}:{version}", "npm", "npm-file", {"name": name, "version": version, "document": item, "tags": document.get("dist-tags", {}), "sha512": base64.b64decode(sha512[7:]).hex()})
            for field in ("dependencies", "optionalDependencies", "peerDependencies"):
                for dependency, dependency_spec in item.get(field, {}).items():
                    self.package("npm", dependency, dependency_spec)

    def npm_file(self, job):
        from semantic_version import Version
        name, version = job["name"], job["version"]
        root = self.root / "repositories/npm"
        encoded = quote(name, safe="")
        self.downloader.fetch(job["document"]["dist"]["tarball"], root / "packages" / encoded / version / "package.tgz", "npm", job["sha512"], "sha512")
        path = root / "metadata" / f"{encoded}.json"
        document = json.loads(path.read_text()) if path.exists() else {"name": name, "versions": {}, "dist-tags": {}}
        document["versions"][version] = job["document"]
        document["dist-tags"].update({tag: value for tag, value in job["tags"].items() if value in document["versions"]})
        document["dist-tags"]["latest"] = max(document["versions"], key=Version)
        atomic_json(path, document)

    def ubuntu_keyring(self):
        fingerprint = "F6ECB3762474EDA9D21B7022871920D1991BC93C"
        key = self.state / "ubuntu-key.asc"
        self.downloader.fetch(f"https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x{fingerprint}", key, "ubuntu")
        home = self.state / "gnupg"
        home.mkdir(mode=0o700, exist_ok=True)
        result = subprocess.run(["gpg", "--homedir", str(home), "--batch", "--with-colons", "--show-keys", str(key)], check=True, capture_output=True, text=True)
        fingerprints = [line.split(":")[9] for line in result.stdout.splitlines() if line.startswith("fpr:")]
        if not fingerprints or fingerprints[0] != fingerprint:
            raise ValueError("Ubuntu signing-key fingerprint mismatch")
        target = self.state / "ubuntu.gpg"
        subprocess.run(["gpg", "--homedir", str(home), "--batch", "--yes", "--dearmor", "--output", str(target), str(key)], check=True, capture_output=True)
        return target

    def apt_index(self, job):
        from debian.deb822 import Deb822, Packages, Release
        registry, suite, base = job["registry"], job["suite"], job["base"]
        stage = self.state / "apt" / registry / suite
        inrelease = self.downloader.fetch(f"{base}/dists/{suite}/InRelease", stage / "InRelease", registry)
        keyring = self.ubuntu_keyring() if job["keyring"] == "ubuntu.gpg" else Path(job["keyring"])
        release_path = stage / "Release"
        release_path.unlink(missing_ok=True)
        subprocess.run(["gpgv", "--keyring", str(keyring), "--output", str(release_path), str(inrelease)], check=True, capture_output=True)
        with release_path.open() as handle:
            release = Release(handle)
        if release.get("Valid-Until") and parsedate_to_datetime(release["Valid-Until"]) < datetime.now(timezone.utc):
            raise ValueError("APT Release has expired")
        entries = {item["name"]: item for item in release["SHA256"]}
        selected = []
        total_bytes = 0
        for component in job["components"]:
            path = f"{component}/binary-amd64/Packages.xz"
            if path not in entries:
                continue
            entry = entries[path]
            url = f"{base}/dists/{suite}/{component}/binary-amd64/by-hash/SHA256/{entry['sha256']}"
            index = self.downloader.fetch(url, stage / path, registry, entry["sha256"], size=int(entry["size"]))
            rows = []
            with lzma.open(index, "rt", encoding="utf-8") as handle:
                for package in Packages.iter_paragraphs(handle, use_apt_pkg=False):
                    filename = safe_relative(package["Filename"])
                    size = int(package["Size"])
                    rows.append({"url": f"{base}/{filename}", "filename": filename, "size": size, "sha256": package["SHA256"], "suite": suite})
            component_bytes = sum(row["size"] for row in rows)
            available = self.config["budgets_bytes"][registry] - self.meter.get(registry)
            if total_bytes + component_bytes > available * 0.95:
                print(f"SKIP oversized APT component {registry}/{suite}/{component}: {component_bytes / 1e9:.2f} GB", flush=True)
                continue
            total_bytes += component_bytes
            selected.append(path)
            for row in rows:
                self.enqueue(f"apt-file:{registry}:{suite}:{row['filename']}", registry, "apt-file", row)
        atomic_json(stage / "selection.json", {"indexes": selected, "planned_bytes": total_bytes})
        self.enqueue(f"apt-publish:{registry}:{suite}", registry, "apt-publish", job)
        print(f"APT planned {registry}/{suite}: {total_bytes / 1e9:.2f} GB", flush=True)

    def apt_file(self, registry, job):
        self.downloader.fetch(job["url"], self.root / "repositories" / registry / job["filename"], registry, job["sha256"], size=job["size"])

    def apt_publish(self, registry, job):
        suite = job["suite"]
        pending = self.db.execute("SELECT payload,status FROM jobs WHERE registry=? AND kind='apt-file' AND status!='done'", (registry,)).fetchall()
        if any(json.loads(payload)["suite"] == suite for payload, _ in pending):
            raise OSError("APT suite still has unfinished downloads")
        stage = self.state / "apt" / registry / suite
        destination = self.root / "repositories" / registry / "dists" / suite
        selection = json.loads((stage / "selection.json").read_text())
        if not selection["indexes"]:
            return
        from debian.deb822 import Release
        with (stage / "Release").open() as handle:
            release = Release(handle)
        if release.get("Valid-Until") and parsedate_to_datetime(release["Valid-Until"]) < datetime.now(timezone.utc):
            raise ValueError("Downloaded APT snapshot expired; not publishing")
        for relative in selection["indexes"]:
            source = stage / relative
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            digest = Downloader.digest(source, "sha256")
            by_hash = target.parent / "by-hash/SHA256" / digest
            by_hash.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, by_hash)
        shutil.copyfile(stage / "InRelease", destination / "InRelease.new")
        os.replace(destination / "InRelease.new", destination / "InRelease")
        print(f"PUBLISHED verified APT snapshot {registry}/{suite}", flush=True)

    def report(self, state="running"):
        counts = dict(self.db.execute("SELECT status,COUNT(*) FROM jobs GROUP BY status").fetchall())
        report = {"campaign": self.config["id"], "state": state, "updated": datetime.now(timezone.utc).isoformat(), "charged_bytes": self.meter.get("payload_bytes"), "payload_limit_bytes": self.config["payload_limit_bytes"], "machine_network_bytes": self.meter.get("interface_bytes"), "registries": {name: self.meter.get(name) for name in self.config["budgets_bytes"]}, "jobs": counts}
        atomic_json(self.state / "status.json", report)
        return report

    def run(self):
        self.setup_django()
        self.seed()
        self.report()
        while True:
            self.meter.sample_interface()
            row = self.db.execute("SELECT id,registry,kind,payload,attempts FROM jobs WHERE status='pending' AND next_try<=? ORDER BY CASE kind WHEN 'pypi-file' THEN 0 WHEN 'npm-file' THEN 0 WHEN 'metadata' THEN 1 WHEN 'apt-file' THEN 2 WHEN 'apt-publish' THEN 3 ELSE 4 END,id LIMIT 1", (time.time(),)).fetchone()
            if row is None:
                pending = self.db.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
                if not pending:
                    self.report("finished")
                    print("Campaign queue finished; unused allowance will not be consumed.", flush=True)
                    return
                self.report("waiting-for-retry")
                time.sleep(30)
                continue
            ident, registry, kind, payload, attempts = row
            job = json.loads(payload)
            print(f"JOB {ident} {registry} {kind}: {job.get('filename', job.get('name', job.get('suite', '')))}", flush=True)
            try:
                if kind == "metadata":
                    (self.pypi_metadata if registry == "pypi" else self.npm_metadata)(job)
                elif kind == "pypi-file":
                    self.pypi_file(job)
                elif kind == "npm-file":
                    self.npm_file(job)
                elif kind == "apt-index":
                    self.apt_index(job)
                elif kind == "apt-file":
                    self.apt_file(registry, job)
                else:
                    self.apt_publish(registry, job)
                with self.db:
                    self.db.execute("UPDATE jobs SET status='done',error='' WHERE id=?", (ident,))
            except RegistryBudgetReached:
                with self.db:
                    self.db.execute("UPDATE jobs SET status='budget-stopped' WHERE registry=? AND status='pending'", (registry,))
                print(f"Registry transfer budget reached: {registry}", flush=True)
            except BudgetReached:
                raise
            except Exception as exc:
                permanent = isinstance(exc, HTTPError) and exc.code in (400, 401, 403, 404, 410)
                connection_error = isinstance(exc, (OSError, URLError, http.client.HTTPException)) and not permanent
                status = "failed" if permanent or (attempts >= 11 and not connection_error) else "pending"
                with self.db:
                    self.db.execute("UPDATE jobs SET status=?,attempts=attempts+1,next_try=?,error=? WHERE id=?", (status, time.time() + min(3600, 60 * 2 ** min(attempts, 6)), str(exc)[:1000], ident))
                print(f"{status.upper()}: {exc}", flush=True)
            self.report()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "status"])
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    state = Path(config["data_root"]) / "sync-state" / config["id"]
    if args.command == "status":
        print((state / "status.json").read_text() if (state / "status.json").exists() else "Not started")
        return
    state.mkdir(parents=True, exist_ok=True)
    with (state / "campaign.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        campaign = Campaign(config)
        try:
            campaign.run()
        except BudgetReached as exc:
            campaign.report("budget-stopped")
            print(f"STOPPED: {exc}", flush=True)


if __name__ == "__main__":
    main()
