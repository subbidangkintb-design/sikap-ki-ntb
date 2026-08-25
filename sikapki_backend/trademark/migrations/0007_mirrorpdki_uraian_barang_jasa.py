from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trademark', '0006_klasifikasimereklog'),
    ]

    operations = [
        migrations.AddField(
            model_name='mirrorpdki',
            name='uraian_barang_jasa',
            field=models.TextField(
                blank=True,
                help_text=(
                    'Uraian barang/jasa untuk kelas ini sebagaimana tercantum pada sumber '
                    'resmi. Jangan diisi dengan ringkasan buatan AI.'
                ),
            ),
        ),
    ]
