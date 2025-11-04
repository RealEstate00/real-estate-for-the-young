"""
Conversation and Message serializers
"""
from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    """Message serializer"""

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'role', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Conversation serializer (without messages)"""

    class Meta:
        model = Conversation
        fields = ['id', 'user', 'title', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Conversation serializer with messages"""

    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'user', 'title', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ChatRequestSerializer(serializers.Serializer):
    """Chat request serializer"""

    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    message = serializers.CharField(required=True, min_length=1)
    model_type = serializers.CharField(default='ollama')


class ChatResponseSerializer(serializers.Serializer):
    """Chat response serializer"""

    conversation_id = serializers.IntegerField()
    user_message = MessageSerializer()
    assistant_message = MessageSerializer()
    sources = serializers.ListField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_null=True)
