from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('classroom', '0003_alter_classroom_class_code'),
        ('materials', '0002_rename_uploaded_at_document_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='classroom',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='documents',
                to='classroom.classroom',
            ),
        ),
    ]
