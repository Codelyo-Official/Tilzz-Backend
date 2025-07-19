from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from storyapp.models import StoryInvite

User = get_user_model()

@receiver(post_save, sender=User)
def assign_invites_to_new_user(sender, instance, created, **kwargs):
    if created and instance.email:
        StoryInvite.objects.filter(
            invited_email__iexact=instance.email,
            invited_user__isnull=True
        ).update(invited_user=instance)
