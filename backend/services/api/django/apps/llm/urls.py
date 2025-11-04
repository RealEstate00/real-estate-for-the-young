"""
LLM Integration URLs
"""
from django.urls import path
from . import views

app_name = 'llm'

urlpatterns = [
    path('chat', views.chat_view, name='chat'),
    path('ask', views.ask_view, name='ask'),
    path('clear-memory', views.clear_memory_view, name='clear-memory'),
]
