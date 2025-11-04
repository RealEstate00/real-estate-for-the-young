"""
Authentication admin
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""

    list_display = ['email', 'username', 'full_name', 'is_active', 'is_verified', 'created_at']
    list_filter = ['is_active', 'is_verified', 'is_staff', 'is_superuser']
    search_fields = ['email', 'username', 'full_name']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('full_name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'full_name'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login']
