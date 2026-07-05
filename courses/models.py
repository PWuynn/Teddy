from django.db import models
from django.conf import settings
import random
import string


JOIN_PERMISSION_CHOICES = (
    ('public', 'Cong khai'),
    ('approval', 'Yeu cau kiem duyet'),
)


MEMBERSHIP_STATUS_CHOICES = (
    ('pending', 'Cho duyet'),
    ('approved', 'Da chap nhan'),
    ('rejected', 'Tu choi'),
)


def generate_course_code():
    while True:
        code = ''.join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=6
            )
        )

        if not Course.objects.filter(course_code=code).exists():
            return code


class Course(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_courses'
    )

    course_code = models.CharField(
        max_length=6,
        unique=True,
        default=generate_course_code,
        blank=True
    )

    qr_code = models.ImageField(
        upload_to='qr_codes/',
        blank=True,
        null=True
    )
    max_members_per_class = models.IntegerField(default=50)
    total_classes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    join_permission = models.CharField(
        max_length=20,
        choices=JOIN_PERMISSION_CHOICES,
        default='public'
    )

    def __str__(self):
        return self.name
    
def generate_class_code():
    from classroom.models import Classroom
    while True:
        code = ''.join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=6
            )
        )

        if not Classroom.objects.filter(class_code=code).exists():
            return code


class CourseMember(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_memberships'
    )

    status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_STATUS_CHOICES,
        default='pending'
    )

    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_course_memberships'
    )

    class Meta:
        unique_together = ('course', 'user')
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.user} - {self.course} ({self.status})"
