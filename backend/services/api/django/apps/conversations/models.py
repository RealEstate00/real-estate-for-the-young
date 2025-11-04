"""
Conversation and Message models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Conversation(models.Model):
    """Conversation model"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name='User'
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Title'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Created at'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated at'
    )

    class Meta:
        db_table = '"auth"."conversations"'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-updated_at']
        managed = False  # Use existing table
        indexes = [
            models.Index(fields=['user', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class Message(models.Model):
    """Message model"""

    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Conversation'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name='Role'
    )
    content = models.TextField(
        verbose_name='Content'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Created at'
    )

    class Meta:
        db_table = '"auth"."messages"'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']
        managed = False  # Use existing table
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"

    def save(self, *args, **kwargs):
        """Override save to update conversation's updated_at"""
        super().save(*args, **kwargs)
        self.conversation.updated_at = timezone.now()
        self.conversation.save(update_fields=['updated_at'])
