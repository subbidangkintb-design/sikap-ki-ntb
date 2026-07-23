import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0003_percakapanchatbot_batas_tindak_lanjut_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='percakapanchatbot',
            name='sesi_id',
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                help_text='ID anonim yang menghubungkan beberapa tanya-jawab dalam satu sesi pengguna.',
            ),
        ),
    ]
