from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from storyapp.models import Story

class Profile(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('subadmin', 'Subadmin'),
        ('admin', 'Admin'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    following = models.ManyToManyField(User, related_name='followers', blank=True)
    favorite_stories = models.ManyToManyField(Story, related_name='favorited_by', blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_users')

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
    def image_preview(self):
        if self.profile_picture:
            return mark_safe(f'<img src="{self.profile_picture.url}" width="150" />')
        return "No picture uploaded"


class Organization(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_account_organizations')
    members = models.ManyToManyField(User, related_name='account_organizations', blank=True)
    
    def __str__(self):
        return self.name
