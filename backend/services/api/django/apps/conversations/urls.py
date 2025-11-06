"""
Conversations URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'conversations'

router = DefaultRouter()
router.register(r'', views.ConversationViewSet, basename='conversation')

urlpatterns = [
    # Chat endpoint (LLM integration)
    path('chat/', views.chat_view, name='chat'),

    # Conversation CRUD (REST)
    path('', include(router.urls)),
]
