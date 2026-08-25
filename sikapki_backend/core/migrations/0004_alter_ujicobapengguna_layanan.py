from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_ujicobapengguna_monitoringsnapshot_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ujicobapengguna',
            name='layanan',
            field=models.CharField(
                choices=[
                    ('keseluruhan', 'Keseluruhan portal'),
                    ('chatbot', 'Chatbot Helpdesk KI'),
                    ('cek_merek', 'Asisten klasifikasi awal merek'),
                    ('checklist', 'Checklist dokumen'),
                    ('informasi', 'Pusat informasi'),
                ],
                max_length=20,
            ),
        ),
    ]
