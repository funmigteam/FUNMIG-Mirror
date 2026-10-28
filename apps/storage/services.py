import shutil
from dataclasses import dataclass
from django.conf import settings
from apps.artifacts.models import Blob

class StorageFull(Exception): pass

@dataclass(frozen=True)
class StorageUsage:
    used: int
    reserved: int
    limit: int
    free_on_disk: int

class StorageManager:
    def get_usage(self):
        root = settings.MIRROR_STORAGE_ROOT
        root.mkdir(parents=True, exist_ok=True)
        disk = shutil.disk_usage(root)
        used = Blob.objects.aggregate(total=__import__("django.db.models", fromlist=["Sum"]).Sum("size"))["total"] or 0
        return StorageUsage(used, 0, settings.STORAGE_LIMITS["total"], disk.free)
    def can_store(self, size, registry="pypi"):
        usage = self.get_usage()
        registry_limit = settings.STORAGE_LIMITS.get(registry, usage.limit)
        registry_used = Blob.objects.filter(artifacts__package_version__package__registry=registry).distinct().aggregate(total=__import__("django.db.models", fromlist=["Sum"]).Sum("size"))["total"] or 0
        return usage.used + size <= usage.limit and registry_used + size <= registry_limit and usage.free_on_disk - size >= settings.STORAGE_LIMITS["min_free"]
    def ensure_can_store(self, size, registry="pypi"):
        if not self.can_store(size, registry):
            raise StorageFull("Storage quota or emergency free-space reserve would be exceeded.")
