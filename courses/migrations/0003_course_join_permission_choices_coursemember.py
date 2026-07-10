from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0002_alter_course_course_code_delete_classroom'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='join_permission',
            field=models.CharField(
                choices=[
                    ('public', 'Cong khai'),
                    ('approval', 'Yeu cau kiem duyet'),
                ],
                default='public',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='CourseMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Chờ duyệt'),
                        ('approved', 'Đã chấp nhận'),
                        ('rejected', 'Tu choi'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='courses.course')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_course_memberships', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='course_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-requested_at'],
                'unique_together': {('course', 'user')},
            },
        ),
    ]
