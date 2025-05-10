"""
URL configuration for story_project project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/stories/', include('storyapp.urls')),
    path('api/accounts/', include('accounts.urls')),
]
