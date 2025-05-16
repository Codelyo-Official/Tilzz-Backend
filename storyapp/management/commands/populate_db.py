from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from storyapp.models import Organization, Story, Version, Episode, StoryReport
from accounts.models import Profile
from django.utils import timezone
import random
from faker import Faker
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Populates the database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating database...')
        
        # Initialize Faker
        fake = Faker()
        
        # Create users if they don't exist
        users = []
        for i in range(1, 10):  # Increased number of users
            username = f'user{i}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name()
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                
                # Update profile with more details
                user.profile.bio = fake.paragraph(nb_sentences=3)
                user.profile.role = random.choice(['user', 'user', 'user', 'subadmin', 'admin'])
                user.profile.save()
                
                self.stdout.write(f'Created user: {username} with role {user.profile.role}')
            users.append(user)
        
        # Set up following relationships between users
        for user in users:
            # Each user follows 1-5 random other users
            for followed_user in random.sample([u for u in users if u != user], random.randint(1, 5)):
                user.profile.following.add(followed_user)
            self.stdout.write(f'Set up following relationships for {user.username}')
        
        # Create organizations
        orgs = []
        for i in range(1, 5):  # Increased number of organizations
            org_name = f"{fake.company()} {fake.company_suffix()}"
            # Check the actual fields in your Organization model
            # Remove 'created_by' if it doesn't exist
            org, created = Organization.objects.get_or_create(
                name=org_name,
                defaults={
                    'description': fake.catch_phrase(),
                    # Remove or replace the created_by field based on your model
                }
            )
            if created:
                self.stdout.write(f'Created organization: {org.name}')
                # Add some users to the organization
                for user in random.sample(users, random.randint(2, 5)):
                    org.members.add(user)
            orgs.append(org)
        
        # Create stories
        stories = []
        for i in range(1, 20):  # Increased number of stories
            user = random.choice(users)
            org = random.choice(orgs) if random.random() > 0.5 else None
            visibility = random.choice(['public', 'public', 'public', 'private', 'quarantined'])
            
            story, created = Story.objects.get_or_create(
                title=fake.sentence(nb_words=6)[:-1],  # Remove period
                defaults={
                    'description': fake.paragraph(nb_sentences=3),
                    'creator': user,
                    'visibility': visibility,
                    'organization': org
                }
            )
            if created:
                self.stdout.write(f'Created story: {story.title}')
                # Add some likes and follows
                for user in random.sample(users, random.randint(0, 7)):
                    story.liked_by.add(user)
                for user in random.sample(users, random.randint(0, 5)):
                    story.followed_by.add(user)
            stories.append(story)
        
        # Create versions and episodes
        for story in stories:
            # Create 1-3 versions per story
            for v in range(1, random.randint(2, 4)):
                version, created = Version.objects.get_or_create(
                    story=story,
                    version_number=str(v),
                )
                if created:
                    self.stdout.write(f'Created version {v} for story: {story.title}')
                
                # Create 2-5 episodes per version
                previous_episode = None
                for e in range(1, random.randint(3, 6)):
                    episode_creator = random.choice(users)
                    episode, created = Episode.objects.get_or_create(
                        title=f'Episode {e}: {fake.sentence(nb_words=4)[:-1]}',
                        defaults={
                            'content': '\n\n'.join([fake.paragraph(nb_sentences=5) for _ in range(3)]),
                            'version': version,
                            'creator': episode_creator,
                            'parent_episode': previous_episode if v > 1 and e == 1 else None
                        }
                    )
                    if created:
                        self.stdout.write(f'Created episode: {episode.title}')
                    previous_episode = episode
        
        # Create story reports
        for _ in range(10):
            story = random.choice(stories)
            reporter = random.choice([u for u in users if u != story.creator])
            
            report, created = StoryReport.objects.get_or_create(
                story=story,
                reported_by=reporter,
                defaults={
                    'reason': random.choice([
                        'Inappropriate content',
                        'Copyright violation',
                        'Hate speech',
                        'Misinformation',
                        'Spam'
                    ]),
                    'status': random.choice(['pending', 'pending', 'approved', 'rejected'])
                }
            )
            if created:
                self.stdout.write(f'Created report for story: {story.title}')
        
        self.stdout.write(self.style.SUCCESS('Database successfully populated!'))