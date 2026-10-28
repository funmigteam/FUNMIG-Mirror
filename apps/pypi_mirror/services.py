import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from apps.artifacts.models import Artifact, Blob, Package, PackageVersion
from apps.storage.services import StorageManager
from .models import RemoteFile

class UpstreamUnavailable(Exception): pass
class VerificationFailed(Exception): pass

def normalize_name(name):
    import re
    return re.sub(r"[-_.]+", "-", name).lower()

def _request(url, accept):
    if settings.UPSTREAM_MODE == "offline": raise UpstreamUnavailable("PyPI is configured offline")
    try:
        return urlopen(Request(url, headers={"Accept": accept, "User-Agent": "funmig-mirror/0.1"}), timeout=10)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise UpstreamUnavailable(str(exc)) from exc

def refresh_metadata(name):
    normalized = normalize_name(name)
    url = f"{settings.PYPI_UPSTREAM}/simple/{quote(normalized)}/"
    with _request(url, "application/vnd.pypi.simple.v1+json") as response:
        payload = json.load(response)
    package, _ = Package.objects.get_or_create(registry="pypi", normalized_name=normalized, defaults={"display_name": payload.get("name", name)})
    for item in payload.get("files", []):
        digest = item.get("hashes", {}).get("sha256")
        if not digest: continue
        version = item["filename"].split("-")[1] if "-" in item["filename"] else "unknown"
        pv, _ = PackageVersion.objects.get_or_create(package=package, version=version)
        RemoteFile.objects.update_or_create(package_version=pv, filename=item["filename"], defaults={"url": item["url"], "sha256": digest, "requires_python": item.get("requires-python") or "", "yanked": bool(item.get("yanked"))})
    return package

def cache_remote_file(remote):
    if remote.artifact_id: return remote.artifact
    parsed = urlparse(remote.url)
    if parsed.scheme != "https" or parsed.hostname not in {"files.pythonhosted.org", "pypi.org"}:
        raise VerificationFailed("Disallowed PyPI artifact host")
    with _request(remote.url, "application/octet-stream") as response:
        length = int(response.headers.get("Content-Length") or 0)
        if length: StorageManager().ensure_can_store(length, "pypi")
        settings.MIRROR_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(dir=settings.MIRROR_TEMP_ROOT, prefix="pypi-")
        digest = hashlib.sha256(); size = 0
        try:
            with os.fdopen(fd, "wb") as out:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    StorageManager().ensure_can_store(size, "pypi")
                    digest.update(chunk); out.write(chunk)
            actual = digest.hexdigest()
            if actual != remote.sha256: raise VerificationFailed("Downloaded hash does not match PyPI metadata")
            relative = f"{actual[:2]}/{actual[2:4]}/{actual}"
            target = settings.MIRROR_BLOBS_ROOT / relative
            with transaction.atomic():
                blob, created = Blob.objects.get_or_create(sha256=actual, defaults={"size": size, "relative_path": relative, "reference_count": 0})
                if created:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(temp_name, target)
                    target.chmod(0o644)
                artifact = Artifact.objects.create(package_version=remote.package_version, filename=remote.filename, upstream_url=remote.url, expected_sha256=remote.sha256, blob=blob)
                blob.reference_count += 1; blob.save(update_fields=["reference_count"])
                remote.artifact = artifact; remote.save(update_fields=["artifact"])
                return artifact
        finally:
            if os.path.exists(temp_name): os.unlink(temp_name)

def touch(artifact):
    artifact.download_count += 1; artifact.last_accessed_at = timezone.now()
    artifact.save(update_fields=["download_count", "last_accessed_at"])
