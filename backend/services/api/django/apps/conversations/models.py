"""
Conversation and Message models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from .encryption import MessageEncryption


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
    """Message model with encrypted content"""

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
        verbose_name='Content (encrypted in DB)'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Created at'
    )

    # Internal field to store encrypted content
    _encrypted_content = None

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
        # Decrypt for display
        try:
            decrypted = MessageEncryption.decrypt(self.content) if self.content else ""
            return f"{self.role}: {decrypted[:50]}"
        except Exception:
            return f"{self.role}: [Encrypted]"

    def save(self, *args, **kwargs):
        """Override save to encrypt content before saving"""
        # Store original plaintext for later use
        original_plaintext = None

        # Encrypt content before saving to database
        if self.content and not self._is_encrypted(self.content):
            original_plaintext = self.content
            self.content = MessageEncryption.encrypt(self.content)
            self._encrypted_content = self.content

        super().save(*args, **kwargs)

        # Restore plaintext content after save (so serializers get decrypted content)
        if original_plaintext is not None:
            self.content = original_plaintext

        # Update conversation's updated_at
        self.conversation.updated_at = timezone.now()
        self.conversation.save(update_fields=['updated_at'])

    @classmethod
    def from_db(cls, db, field_names, values):
        """Override from_db to decrypt content when loading from database"""
        instance = super().from_db(db, field_names, values)

        # Decrypt content after loading from database
        if instance.content:
            try:
                instance._encrypted_content = instance.content
                instance.content = MessageEncryption.decrypt(instance.content)
            except Exception as e:
                # If decryption fails, keep original (might be legacy unencrypted data)
                pass

        return instance

    def _is_encrypted(self, text):
        """Check if text is already encrypted (basic heuristic)"""
        # Fernet encrypted strings start with 'gAAAAA' after base64 encoding
        return text.startswith('gAAAAA') if text else False
