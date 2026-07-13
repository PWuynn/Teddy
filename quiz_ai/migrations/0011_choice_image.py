import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('quiz_ai', '0010_quiz_reload_penalty')]
    operations = [
        migrations.AddField(
            model_name='choice',
            name='image',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True),
        ),
    ]
