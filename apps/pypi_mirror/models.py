from django.db import models
from apps.artifacts.models import Artifact, PackageVersion

class RemoteFile(models.Model):
    package_version = models.ForeignKey(PackageVersion, on_delete=models.CASCADE, related_name="remote_files")
    filename = models.CharField(max_length=512)
    url = models.URLField(max_length=1024)
    sha256 = models.CharField(max_length=64)
    requires_python = models.CharField(max_length=255, blank=True)
    yanked = models.BooleanField(default=False)
    artifact = models.OneToOneField(Artifact, null=True, blank=True, on_delete=models.SET_NULL, related_name="remote_file")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["package_version", "filename"], name="unique_pypi_remote_file")]
