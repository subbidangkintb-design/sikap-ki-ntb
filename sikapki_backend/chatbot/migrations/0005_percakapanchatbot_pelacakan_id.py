import uuid

from django.db import migrations, models


def populate_tracking_ids(apps, schema_editor):
    conversation = apps.get_model('chatbot', 'PercakapanChatbot')
    for row in conversation.objects.filter(pelacakan_id__isnull=True).iterator():
        row.pelacakan_id = uuid.uuid4()
        row.save(update_fields=['pelacakan_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0004_percakapanchatbot_sesi_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='percakapanchatbot',
            name='pelacakan_id',
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_tracking_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='percakapanchatbot',
            name='pelacakan_id',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                help_text='Token acak untuk pelacakan status konsultasi oleh pengguna tanpa login.',
                unique=True,
            ),
        ),
    ]
