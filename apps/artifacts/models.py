from django.db import models

class ArtifactPriority(models.TextChoices):
    CRITICAL = "critical", "Critical"
    HIGH = "high", "High"
    NORMAL = "normal", "Normal"
    LOW = "low", "Low"
    EPHEMERAL = "ephemeral", "Ephemeral"

class Blob(models.Model):
    sha256 = models.CharField(max_length=64, unique=True, db_index=True)
    size = models.BigIntegerField()
    relative_path = models.CharField(max_length=255, unique=True)
    reference_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Package(models.Model):
    registry = models.CharField(max_length=20, db_index=True)
    normalized_name = models.CharField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255)
    is_pinned = models.BooleanField(default=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["registry", "normalized_name"], name="unique_registry_package")]

class PackageVersion(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=128, db_index=True)
    is_pinned = models.BooleanField(default=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["package", "version"], name="unique_package_version")]

class Artifact(models.Model):
    package_version = models.ForeignKey(PackageVersion, on_delete=models.CASCADE, related_name="artifacts")
    filename = models.CharField(max_length=512)
    upstream_url = models.URLField(max_length=1024)
    expected_sha256 = models.CharField(max_length=64, blank=True)
    blob = models.ForeignKey(Blob, on_delete=models.PROTECT, related_name="artifacts")
    priority = models.CharField(max_length=16, choices=ArtifactPriority.choices, default=ArtifactPriority.NORMAL, db_index=True)
    download_count = models.PositiveIntegerField(default=0)
    last_accessed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    cached_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=12, default="verified")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["package_version", "filename"], name="unique_version_filename")]
