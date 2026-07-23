from django.db import migrations


def initialize_status(apps, schema_editor):
    document = apps.get_model('knowledge', 'DokumenResmi')
    verified = document.objects.filter(status_validasi='terverifikasi')
    verified.filter(chunks__isnull=False).distinct().update(status_indexing='berhasil')
    verified.filter(chunks__isnull=True).update(status_indexing='menunggu')


def reset_status(apps, schema_editor):
    document = apps.get_model('knowledge', 'DokumenResmi')
    document.objects.update(status_indexing='belum')


class Migration(migrations.Migration):
    dependencies = [
        ('knowledge', '0003_dokumenresmi_indexing_dimulai_pada_and_more'),
    ]

    operations = [
        migrations.RunPython(initialize_status, reset_status),
    ]
