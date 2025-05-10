from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(User, related_name='organizations')
    
    def __str__(self):
        return self.name

class Story(models.Model):
    PUBLIC = 'public'
    PRIVATE = 'private'
    QUARANTINED = 'quarantined'
    VISIBILITY_CHOICES = [
        (PUBLIC, 'Public'),
        (PRIVATE, 'Private'),
        (QUARANTINED, 'Quarantined'),
    ]
#    visibility = models.CharField(max_length=20, choices=[('public', 'Public'), ('private', 'Private')], default='public')

    title = models.CharField(max_length=255)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    liked_by = models.ManyToManyField(User, related_name='liked_stories', blank=True)
    followed_by = models.ManyToManyField(User, related_name='followed_stories', blank=True)
    visibility = models.CharField(max_length=15, choices=VISIBILITY_CHOICES, default=PUBLIC)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cover_image = models.ImageField(upload_to='story_covers/', null=True, blank=True)
    
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='stories')

    def __str__(self):
        return self.title


class Version(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.story.title} - v{self.version_number}"


class Episode(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE, related_name='episodes')
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent_version = models.ForeignKey(Version, on_delete=models.SET_NULL, null=True, blank=True, related_name='branched_episodes')

    def __str__(self):
        return self.title


class StoryReport(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]
    
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)

    def __str__(self):
        return f"Report on '{self.story.title}' by {self.reported_by.username}"
