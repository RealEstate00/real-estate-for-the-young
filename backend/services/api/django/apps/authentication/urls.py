"""
Authentication URLs
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'authentication'

urlpatterns = [
    # Registration & Login
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # JWT Token Refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User Info
    path('me/', views.me_view, name='me'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
]
