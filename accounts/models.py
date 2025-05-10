from django.db import models
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from storyapp.models import Story

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    following = models.ManyToManyField(User, related_name='followers', blank=True)
    favorite_stories = models.ManyToManyField(Story, related_name='favorited_by', blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
    def image_preview(self):
        if self.profile_picture:
            return mark_safe(f'<img src="{self.profile_picture.url}" width="150" />')
        return "No picture uploaded"
