from django.db import models
from django.conf import settings
from classroom.models import Classroom
from .storage import DocumentCloudinaryStorage

class Document(models.Model):

    LEVEL_CHOICES = [
        ('Tiểu học', 'Tiểu học'),
        ('THCS', 'THCS'),
        ('THPT', 'THPT'),
        ('Đại học', 'Đại học'),
    ]

    PERMISSION_CHOICES = [
        ('view', 'Chỉ xem'),
        ('download', 'Xem và tải'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255)

    description = models.TextField(
        blank=True,
        null=True
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='THPT'
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )
    subject = models.CharField(
        max_length=100,
        default='khác'
    )

    file = models.FileField(
        upload_to='documents/',
        storage=DocumentCloudinaryStorage() if settings.USE_CLOUDINARY_MEDIA else None
    )

    permission = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default='download'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title