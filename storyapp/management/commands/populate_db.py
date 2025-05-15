from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from storyapp.models import Organization, Story, Version, Episode
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Populates the database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating database...')
        
        # Create users if they don't exist
        users = []
        for i in range(1, 6):
            username = f'user{i}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'password': 'password123',  # In production, use set_password()
                    'first_name': f'First{i}',
                    'last_name': f'Last{i}'
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'Created user: {username}')
            users.append(user)
        
        # Create organizations
        orgs = []
        for i in range(1, 3):
            org, created = Organization.objects.get_or_create(
                name=f'Organization {i}',
                defaults={'description': f'Description for Organization {i}'}
            )
            if created:
                self.stdout.write(f'Created organization: {org.name}')
                # Add some users to the organization
                for user in random.sample(users, 2):
                    org.members.add(user)
            orgs.append(org)
        
        # Create stories
        stories = []
        for i in range(1, 10):
            user = random.choice(users)
            org = random.choice(orgs) if random.random() > 0.5 else None
            visibility = random.choice(['public', 'private'])
            
            story, created = Story.objects.get_or_create(
                title=f'Story {i}',
                defaults={
                    'description': f'Description for Story {i}',
                    'creator': user,
                    'visibility': visibility,
                    'organization': org
                }
            )
            if created:
                self.stdout.write(f'Created story: {story.title}')
                # Add some likes and follows
                for user in random.sample(users, random.randint(0, 3)):
                    story.liked_by.add(user)
                for user in random.sample(users, random.randint(0, 2)):
                    story.followed_by.add(user)
            stories.append(story)
        
        # Create versions and episodes
        for story in stories:
            # Create 1-3 versions per story
            for v in range(1, random.randint(2, 4)):
                version, created = Version.objects.get_or_create(
                    story=story,
                    version_number=v,
                )
                if created:
                    self.stdout.write(f'Created version {v} for story: {story.title}')
                
                # Create 2-5 episodes per version
                previous_episode = None
                for e in range(1, random.randint(3, 6)):
                    episode_creator = random.choice(users)
                    episode, created = Episode.objects.get_or_create(
                        title=f'Episode {e} of Version {v}',
                        defaults={
                            'content': f'Content for episode {e} of version {v} for story {story.title}',
                            'version': version,
                            'creator': episode_creator,
                            'parent_episode': previous_episode if v > 1 and e == 1 else None
                        }
                    )
                    if created:
                        self.stdout.write(f'Created episode: {episode.title}')
                    previous_episode = episode
        
        self.stdout.write(self.style.SUCCESS('Database successfully populated!'))