from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from storyapp.models import Story

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    following = models.ManyToManyField(User, related_name='followers', blank=True)
    favorite_stories = models.ManyToManyField(Story, related_name='favorited_by', blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Story(models.Model):
    pass


class Version(models.Model):
    pass


class Episode(models.Model):
    pass


class StoryReport(models.Model):
    pass
