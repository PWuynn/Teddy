from django.db import models
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
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name='Anh dai dien'
    )
