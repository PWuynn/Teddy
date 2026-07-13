from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser
class CustomUser(AbstractUser):

    ROLE_CHOICES = (
        ('student', 'Học sinh'),
        ('teacher', 'Giáo viên'),
        ('admin', 'Quản trị'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student'
    )
    
    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'admin'
        super().save(*args, **kwargs)

    full_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Ho ten'
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Ngay sinh'
    )
    school = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Truong'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='So dien thoai'
    )
    bio = models.TextField(
        blank=True,
        verbose_name='Mo ta khac'
    )
    if settings.USE_CLOUDINARY_MEDIA:
        avatar = CloudinaryField(
            folder='teddy/avatars',
            null=True,
            blank=True,
            verbose_name="Anh dai dien",
        )
    else:
        avatar = models.ImageField(
            upload_to="avatars/",
            null=True,
            blank=True,
            verbose_name="Anh dai dien",
        )
    @property
    def is_admin(self):
        return self.is_superuser or self.role == 'admin'

    @property
    def is_teacher(self):
        return self.role == 'teacher'

    @property
    def is_student(self):
        return self.role == 'student'