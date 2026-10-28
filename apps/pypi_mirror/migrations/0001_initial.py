import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('artifacts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RemoteFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=512)),
                ('url', models.URLField(max_length=1024)),
                ('sha256', models.CharField(max_length=64)),
                ('requires_python', models.CharField(blank=True, max_length=255)),
                ('yanked', models.BooleanField(default=False)),
                ('artifact', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='remote_file', to='artifacts.artifact')),
                ('package_version', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remote_files', to='artifacts.packageversion')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('package_version', 'filename'), name='unique_pypi_remote_file')],
            },
        ),
    ]
