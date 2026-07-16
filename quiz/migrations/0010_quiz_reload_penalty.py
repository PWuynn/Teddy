from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0009_cloudinary_images'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuizReloadPenalty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('quiz', models.ForeignKey(on_delete=models.deletion.CASCADE, to='quiz.quiz')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
