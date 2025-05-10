from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    following = models.ManyToManyField(User, related_name='followers', blank=True)
    favorite_stories = models.ManyToManyField('storyapp.Story', related_name='favorited_by', blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"


class Story(models.Model):
    pass


class Version(models.Model):
    pass


class Episode(models.Model):
    pass


class StoryReport(models.Model):
    pass
