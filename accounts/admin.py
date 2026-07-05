from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Ho so', {
            'fields': (
                'full_name',
                'birth_date',
                'school',
                'phone',
                'bio',
            )
        }),
    )
    list_display = (
        'username',
        'email',
        'full_name',
        'role',
        'is_staff',
    )
