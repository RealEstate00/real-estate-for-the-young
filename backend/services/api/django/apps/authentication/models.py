"""
Custom User model for authentication
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager"""

    def create_user(self, email, username, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model"""

    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name='Email address'
    )
    username = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Username'
    )
    full_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Full name'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active status'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Staff status'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Email verified'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Created at'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated at'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = '"auth"."users"'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        managed = False  # Use existing table

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        """Override save to update updated_at"""
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
