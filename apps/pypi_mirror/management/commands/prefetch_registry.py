import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from packaging.version import InvalidVersion, Version

from apps.pypi_mirror.models import RemoteFile
from apps.pypi_mirror.services import cache_remote_file, normalize_name, refresh_metadata

GIB = 1024 ** 3
PROJECT = Path(__file__).resolve().parents[4]


def package_names(path):
    seen = set()
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        name = raw.strip()
        if not name or name.startswith("#") or name in seen:
            continue
        seen.add(name)
        yield name


def version_key(value):
    try:
        return (1, Version(value))
    except InvalidVersion:
        return (0, value)


def wanted_python_file(filename):
    lower = filename.lower()
    if lower.endswith((".tar.gz", ".tar.bz2", ".zip")):
        return True
    if not lower.endswith(".whl"):
        return False
    return any(marker in lower for marker in ("none-any.whl", "manylinux", "musllinux", "linux_x86_64"))


class Command(BaseCommand):
    help = "Prefetch a curated PyPI or npm package list with integrity checks and a hard quota."

    def add_arguments(self, parser):
        parser.add_argument("--registry", choices=("pypi", "npm"), required=True)
        parser.add_argument("--package-list", required=True)
        parser.add_argument("--versions", type=int, required=True)
        parser.add_argument("--budget-gib", type=int, required=True)

    def handle(self, *args, **options):
        if options["versions"] < 1 or options["budget_gib"] < 1:
            raise CommandError("versions and budget must be positive")
        if options["registry"] == "pypi":
            self.prefetch_pypi(options)
        else:
            self.prefetch_npm(options)

    def prefetch_pypi(self, options):
        for name in package_names(options["package_list"]):
            self.stdout.write(f"pypi metadata: {name}")
            refresh_metadata(name)
            files = RemoteFile.objects.filter(
                package_version__package__registry="pypi",
                package_version__package__normalized_name=normalize_name(name),
            ).select_related("package_version", "artifact__blob")
            versions = sorted({item.package_version.version for item in files}, key=version_key, reverse=True)[: options["versions"]]
            for item in files:
                if item.package_version.version in versions and wanted_python_file(item.filename):
                    cache_remote_file(item)

    def prefetch_npm(self, options):
        config = json.loads((PROJECT / "sync" / "mirror-sync.json").read_text(encoding="utf-8"))
        npm_config = config["registries"]["npm"]
        root = Path(config["data_root"]) / "npm"
        package_root, metadata_root, temp_root = root / "packages", root / "metadata", root / "temp"
        for path in (package_root, metadata_root, temp_root):
            path.mkdir(parents=True, exist_ok=True)
        limit = options["budget_gib"] * GIB
        registry = npm_config["registry"].rstrip("/")
        for name in package_names(options["package_list"]):
            safe_name = quote(name, safe="")
            with urlopen(Request(f"{registry}/{safe_name}", headers={"Accept": "application/json", "User-Agent": "funmig-mirror/1"}), timeout=30) as response:
                metadata = json.load(response)
            versions = sorted(metadata.get("versions", {}).keys(), key=version_key, reverse=True)[: options["versions"]]
            selected = {version: metadata["versions"][version] for version in versions}
            metadata_file = metadata_root / f"{safe_name}.json"
            metadata_file.write_text(json.dumps({"name": name, "dist-tags": metadata.get("dist-tags", {}), "versions": selected}, ensure_ascii=False) + "\n", encoding="utf-8")
            for version, document in selected.items():
                dist = document.get("dist", {})
                tarball, integrity = dist.get("tarball"), dist.get("integrity")
                if not tarball or not integrity or not integrity.startswith("sha512-"):
                    raise CommandError(f"{name}@{version}: sha512 integrity is required")
                target_dir = package_root / safe_name / version
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / "package.tgz"
                if target.exists():
                    continue
                with urlopen(Request(tarball, headers={"User-Agent": "funmig-mirror/1"}), timeout=60) as response:
                    expected_size = int(response.headers.get("Content-Length") or 0)
                    if directory_size(root) + expected_size > limit:
                        raise CommandError("npm quota would be exceeded")
                    fd, temp_name = tempfile.mkstemp(dir=temp_root, prefix="npm-")
                    digest = hashlib.sha512()
                    try:
                        with os.fdopen(fd, "wb") as output:
                            while chunk := response.read(1024 * 1024):
                                digest.update(chunk)
                                output.write(chunk)
                        expected = base64.b64decode(integrity.removeprefix("sha512-"))
                        if digest.digest() != expected:
                            raise CommandError(f"{name}@{version}: integrity verification failed")
                        os.replace(temp_name, target)
                        target.chmod(0o644)
                    finally:
                        if os.path.exists(temp_name):
                            os.unlink(temp_name)


def directory_size(path):
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
