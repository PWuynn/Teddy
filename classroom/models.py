import uuid

from django.conf import settings
from django.db import models

from courses.models import Course


JOIN_CHOICES = (
    ('free', 'Cong khai'),
    ('approval', 'Yeu cau kiem duyet'),
)

MEMBER_STATUS_CHOICES = (
    ('pending', 'Cho duyet'),
    ('approved', 'Da chap nhan'),
    ('rejected', 'Tu choi'),
)


class Classroom(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='classes',
        blank=True,
        null=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_classrooms'
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='joined_classrooms',
        blank=True
    )
    class_code = models.CharField(max_length=8, unique=True)
    max_members = models.IntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    join_permission = models.CharField(
        max_length=20,
        choices=JOIN_CHOICES,
        default='free'
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.class_code:
            self.class_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)


class ClassroomMember(models.Model):
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='members'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=MEMBER_STATUS_CHOICES,
        default='approved'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_classroom_memberships'
    )

    class Meta:
        unique_together = ('classroom', 'student')

    def __str__(self):
        return f"{self.student} - {self.classroom} ({self.status})"
