from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
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
    avatar = CloudinaryField(
    "avatar",
    folder="avatars",
    blank=True,
    null=True,
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