import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Blob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sha256', models.CharField(db_index=True, max_length=64, unique=True)),
                ('size', models.BigIntegerField()),
                ('relative_path', models.CharField(max_length=255, unique=True)),
                ('reference_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Package',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registry', models.CharField(db_index=True, max_length=20)),
                ('normalized_name', models.CharField(db_index=True, max_length=255)),
                ('display_name', models.CharField(max_length=255)),
                ('is_pinned', models.BooleanField(default=False)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('registry', 'normalized_name'), name='unique_registry_package')],
            },
        ),
        migrations.CreateModel(
            name='PackageVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(db_index=True, max_length=128)),
                ('is_pinned', models.BooleanField(default=False)),
                ('package', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='artifacts.package')),
            ],
        ),
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=512)),
                ('upstream_url', models.URLField(max_length=1024)),
                ('expected_sha256', models.CharField(blank=True, max_length=64)),
                ('priority', models.CharField(choices=[('critical', 'Critical'), ('high', 'High'), ('normal', 'Normal'), ('low', 'Low'), ('ephemeral', 'Ephemeral')], db_index=True, default='normal', max_length=16)),
                ('download_count', models.PositiveIntegerField(default=0)),
                ('last_accessed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('cached_at', models.DateTimeField(auto_now_add=True)),
                ('verification_status', models.CharField(default='verified', max_length=12)),
                ('blob', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='artifacts', to='artifacts.blob')),
                ('package_version', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='artifacts.packageversion')),
            ],
        ),
        migrations.AddConstraint(
            model_name='packageversion',
            constraint=models.UniqueConstraint(fields=('package', 'version'), name='unique_package_version'),
        ),
        migrations.AddConstraint(
            model_name='artifact',
            constraint=models.UniqueConstraint(fields=('package_version', 'filename'), name='unique_version_filename'),
        ),
    ]
