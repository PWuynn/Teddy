from django.db import models
from django.conf import settings
from classroom.models import Classroom
from django.utils import timezone

class Todo(models.Model):

    ROLE_CHOICES = (
        ('teacher', 'Giáo viên'),
        ('student', 'Học sinh'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
    )

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='todos'
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_todos'
    )

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    deadline = models.DateTimeField(null=True, blank=True)

    completed = models.BooleanField(default=False)

    submission_text = models.TextField(blank=True)

    submission_file = models.FileField(
        upload_to='submissions/',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
class PersonalTodo(models.Model):

    PRIORITY_CHOICES = (
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        null=True)
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    deadline = models.DateTimeField()
    is_public = models.BooleanField(
        default=False,
        verbose_name="Công khai"
    )
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title