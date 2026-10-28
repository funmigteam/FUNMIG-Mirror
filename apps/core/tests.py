import tempfile
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import reverse


class GitRepositoryViewsTests(TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        (self.root / "django-main.zip").write_bytes(b"PK\x03\x04test")
        self.settings_override = override_settings(GIT_REPOSITORY_ROOT=self.root)
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.temp_directory.cleanup()

    def test_repository_is_listed_with_download_link(self):
        response = self.client.get(reverse("git-repositories"), secure=True)
        self.assertContains(response, "Django")
        self.assertContains(response, "django-main.zip")

    def test_download_is_delegated_to_internal_nginx_location(self):
        response = self.client.get(reverse("git-repository-download", args=["django-main.zip"]), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Accel-Redirect"], "/_git_repositories/django-main.zip")
        self.assertEqual(response["Content-Type"], "application/zip")

    def test_unknown_archive_returns_not_found(self):
        response = self.client.get(reverse("git-repository-download", args=["missing.zip"]), secure=True)
        self.assertEqual(response.status_code, 404)
