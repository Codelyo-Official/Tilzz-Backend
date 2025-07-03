from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(User, related_name='organizations')
    
    def __str__(self):
        return self.name
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
class Story(models.Model):
    PUBLIC = 'public'
    PRIVATE = 'private'
    QUARANTINED = 'quarantined'
    REPORTED = 'reported'  # New status
    VISIBILITY_CHOICES = [
        (PUBLIC, 'Public'),
        (PRIVATE, 'Private'),
        (QUARANTINED, 'Quarantined'),
        (REPORTED, 'Reported'),  # New status
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
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='stories')

    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='stories')

    def __str__(self):
        return self.title


class Version(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.story.title} - v{self.version_number}"

    # When creating a new version, add this method to your Version model
    def save(self, *args, **kwargs):
        # If this is a new version (no ID yet) or version_number was changed
        if not self.pk or self._state.adding:
            # Ensure version_number is padded with leading zeros
            try:
                # Convert to integer first to remove any existing padding
                version_int = int(self.version_number)
                # Pad with 5 zeros (allows for versions up to 99999)
                self.version_number = str(version_int).zfill(5)
            except (ValueError, TypeError):
                # If version_number is not a valid integer, leave it as is
                pass
        
        super().save(*args, **kwargs)


class Episode(models.Model):
    PUBLIC = 'public'
    PRIVATE = 'private'
    QUARANTINED = 'quarantined'
    REPORTED = 'reported'
    PENDING = 'pending'  # New status
    DELETED = 'deleted'  # Add this line
    STATUS_CHOICES = [
        (PUBLIC, 'Public'),
        (PRIVATE, 'Private'),
        (QUARANTINED, 'Quarantined'),
        (REPORTED, 'Reported'),
        (PENDING, 'Pending'),  # New status
        (DELETED, 'Deleted'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    version = models.ForeignKey(Version, on_delete=models.CASCADE, related_name='episodes')
    parent_episode = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_episodes')
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='episodes',null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=PUBLIC)
    liked_by = models.ManyToManyField(User, related_name='liked_episodes', blank=True)
    
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


class EpisodeReport(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]
    
    episode = models.ForeignKey('Episode', on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)

    def __str__(self):
        return f"Report on episode '{self.episode.title}' by {self.reported_by.username}"

    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Check if this episode has 3 or more pending reports
        report_count = EpisodeReport.objects.filter(
            episode=self.episode,
            status=EpisodeReport.PENDING
        ).count()
        
        # If 3 or more pending reports and episode is not already quarantined, quarantine it
        if report_count >= 1 and self.episode.status != Episode.QUARANTINED:
            self.episode.status = Episode.QUARANTINED
            self.episode.save()

