from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0008_personaltodo_completed'),
    ]

    operations = [
        migrations.AddField(
            model_name='todo',
            name='todo_completed',
            field=models.BooleanField(default=False),
        ),
    ]
