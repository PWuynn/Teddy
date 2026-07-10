from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('classroom', '0003_alter_classroom_class_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='classroom',
            name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='classes', to='courses.course'),
        ),
        migrations.AlterField(
            model_name='classroom',
            name='join_permission',
            field=models.CharField(choices=[('free', 'Cong khai'), ('approval', 'Yeu cau kiem duyet')], default='free', max_length=20),
        ),
        migrations.AddField(
            model_name='classroommember',
            name='status',
            field=models.CharField(choices=[('pending', 'Chờ duyệt'), ('approved', 'Đã chấp nhận'), ('rejected', 'Tu choi')], default='approved', max_length=20),
        ),
        migrations.AddField(
            model_name='classroommember',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='classroommember',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_classroom_memberships', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='classroommember',
            unique_together={('classroom', 'student')},
        ),
    ]
