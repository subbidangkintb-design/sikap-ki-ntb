from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trademark', '0005_remove_cekmereklog_ip_pengguna_cekmereklog_ip_hash'),
    ]

    operations = [
        migrations.CreateModel(
            name='KlasifikasiMerekLog',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('nama_merek_diajukan', models.CharField(max_length=255)),
                ('deskripsi_produk', models.TextField()),
                (
                    'rekomendasi_kelas',
                    models.JSONField(
                        default=list,
                        help_text=(
                            'Kandidat kelas dan istilah barang/jasa resmi yang '
                            'direkomendasikan.'
                        ),
                    ),
                ),
                ('perlu_klarifikasi', models.BooleanField(default=False)),
                (
                    'logo_disertakan',
                    models.BooleanField(
                        default=False,
                        help_text=(
                            'Hanya mencatat keberadaan logo; berkas dan isi logo tidak '
                            'disimpan atau dinilai.'
                        ),
                    ),
                ),
                ('dibuat_pada', models.DateTimeField(auto_now_add=True)),
                (
                    'ip_hash',
                    models.CharField(
                        blank=True,
                        editable=False,
                        help_text=(
                            'Sidik anonim untuk mitigasi penyalahgunaan; alamat IP asli '
                            'tidak disimpan.'
                        ),
                        max_length=64,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Log Asisten Klasifikasi Merek',
                'verbose_name_plural': 'Log Asisten Klasifikasi Merek',
                'ordering': ['-dibuat_pada'],
            },
        ),
    ]
