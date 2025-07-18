from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from storyapp.models import StoryInvite
from .models import Profile

@receiver(post_save, sender=User)
def link_story_invites_to_user(sender, instance, created, **kwargs):
    if created:
        # Auto-create profile
        Profile.objects.create(user=instance)

        # Link any pending invites for this email
        StoryInvite.objects.filter(
            invited_email__iexact=instance.email,
            invited_user__isnull=True
        ).update(invited_user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
