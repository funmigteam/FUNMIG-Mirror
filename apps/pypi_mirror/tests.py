from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
from django.test import SimpleTestCase, TestCase, override_settings
from apps.artifacts.models import Blob
from apps.pypi_mirror.services import normalize_name
from apps.storage.services import StorageManager

class NormalizationTests(SimpleTestCase):
    def test_pep_503_normalization(self):
        self.assertEqual(normalize_name("Django_REST.framework"), "django-rest-framework")

class StorageQuotaTests(TestCase):
    @override_settings(STORAGE_LIMITS={"total": 100, "pypi": 70, "npm": 70, "temp": 20, "min_free": 10}, MIRROR_STORAGE_ROOT=Path("/tmp/funmig-mirror-test"))
    @patch("apps.storage.services.shutil.disk_usage")
    def test_total_quota_rejects_download(self, disk_usage):
        disk_usage.return_value = SimpleNamespace(free=900)
        Blob.objects.create(sha256="a" * 64, size=60, relative_path="aa/aa/" + "a" * 64)
        self.assertFalse(StorageManager().can_store(50, "pypi"))
