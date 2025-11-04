"""
Conversations admin
"""
from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    """Message inline for Conversation admin"""
    model = Message
    extra = 0
    fields = ['role', 'content', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Conversation Admin"""

    list_display = ['id', 'user', 'title', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['title', 'user__email', 'user__username']
    ordering = ['-updated_at']
    inlines = [MessageInline]

    fieldsets = (
        (None, {'fields': ('user', 'title')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Message Admin"""

    list_display = ['id', 'conversation', 'role', 'content_preview', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'conversation__title']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('conversation', 'role', 'content')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )

    readonly_fields = ['created_at']

    def content_preview(self, obj):
        """Show first 50 characters of content"""
        return obj.content[:50] if obj.content else ''
    content_preview.short_description = 'Content Preview'
