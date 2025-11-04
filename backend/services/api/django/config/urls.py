"""
URL configuration for Real Estate for the Young API
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def api_root(request):
    return JsonResponse({
        "message": "Real Estate for the Young API",
        "docs": "/api/docs/"
    })

urlpatterns = [
    path('', api_root),
    path('admin/', admin.site.urls),

    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API endpoints
    path('api/auth/', include('apps.authentication.urls')),
    path('api/conversations/', include('apps.conversations.urls')),
    path('api/llm/', include('apps.llm.urls')),
]
