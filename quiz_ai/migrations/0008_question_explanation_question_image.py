# Generated manually for quiz question rich content

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz_ai', '0007_quiz_classroom'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='explanation',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='question',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='quiz_question_images/'),
        ),
    ]
