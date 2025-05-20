from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EpisodeReport, Story

@receiver(post_save, sender=EpisodeReport)
def check_episode_reports(sender, instance, created, **kwargs):
    """
    Signal to automatically quarantine stories when their episodes receive 3 or more reports
    """
    if created:  # Only run this when a new report is created
        episode = instance.episode
        story = episode.version.story
        
        # Count reports for this episode
        report_count = EpisodeReport.objects.filter(episode=episode).count()
        
        # If 3 or more reports, quarantine the story
        if report_count >= 3 and story.visibility != 'quarantined':
            story.visibility = 'quarantined'
            story.save()
            print(f"Story '{story.title}' automatically quarantined due to {report_count} reports on episode '{episode.title}'")