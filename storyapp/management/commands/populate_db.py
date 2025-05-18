from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile, Organization
from storyapp.models import Story, Version, Episode, StoryReport, EpisodeReport
from django.utils import timezone
import random
from django.core.files.uploadedfile import SimpleUploadedFile
import os

class Command(BaseCommand):
    help = 'Populates the database with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating database...')
        
        # Create admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpassword'
            )
            admin_user.profile.role = 'admin'
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.username}'))
        else:
            admin_user = User.objects.get(username='admin')
            self.stdout.write('Admin user already exists')
        
        # Create subadmin users
        subadmins = []
        for i in range(1, 3):
            username = f'subadmin{i}'
            if not User.objects.filter(username=username).exists():
                subadmin = User.objects.create_user(
                    username=username,
                    email=f'subadmin{i}@example.com',
                    password='subadminpassword'
                )
                subadmin.profile.role = 'subadmin'
                subadmin.profile.bio = f'Subadmin {i} bio'
                subadmin.profile.save()
                subadmins.append(subadmin)
                self.stdout.write(self.style.SUCCESS(f'Created subadmin: {subadmin.username}'))
            else:
                subadmins.append(User.objects.get(username=username))
                self.stdout.write(f'Subadmin {username} already exists')
        
        # Create regular users
        users = []
        for i in range(1, 10):
            username = f'user{i}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'user{i}@example.com',
                    password='userpassword'
                )
                user.profile.bio = f'User {i} bio'
                
                # Assign some users to subadmins
                if i % 3 == 0 and subadmins:
                    user.profile.assigned_to = random.choice(subadmins)
                    user.profile.save()
                    self.stdout.write(f'Assigned {user.username} to {user.profile.assigned_to.username}')
                
                users.append(user)
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))
            else:
                users.append(User.objects.get(username=username))
                self.stdout.write(f'User {username} already exists')
        
        # Create organizations
        organizations = []
        for i in range(1, 4):
            org_name = f'Organization {i}'
            if not Organization.objects.filter(name=org_name).exists():
                org = Organization.objects.create(
                    name=org_name,
                    description=f'Description for Organization {i}',
                    created_by=random.choice(subadmins) if subadmins else admin_user
                )
                
                # Add members to organization
                for j in range(3):
                    if users:
                        member = random.choice(users)
                        org.members.add(member)
                
                organizations.append(org)
                self.stdout.write(self.style.SUCCESS(f'Created organization: {org.name}'))
            else:
                organizations.append(Organization.objects.get(name=org_name))
                self.stdout.write(f'Organization {org_name} already exists')
        
        # Create stories
        stories = []
        for i in range(1, 15):
            title = f'Story {i}'
            if not Story.objects.filter(title=title).exists():
                creator = random.choice(users) if users else admin_user
                visibility_choices = ['public', 'private', 'followers']
                
                story = Story.objects.create(
                    title=title,
                    description=f'Description for Story {i}',
                    creator=creator,
                    visibility=random.choice(visibility_choices)
                )
                
                # Add likes and followers
                for j in range(random.randint(0, 5)):
                    if users:
                        liker = random.choice(users)
                        story.liked_by.add(liker)
                
                for j in range(random.randint(0, 3)):
                    if users:
                        follower = random.choice(users)
                        story.followed_by.add(follower)
                
                stories.append(story)
                self.stdout.write(self.style.SUCCESS(f'Created story: {story.title}'))
            else:
                stories.append(Story.objects.get(title=title))
                self.stdout.write(f'Story {title} already exists')
        
        # Create versions and episodes
        for story in stories:
            # Create at least one version for each story
            if not Version.objects.filter(story=story).exists():
                version = Version.objects.create(
                    story=story,
                    version_number='00001'  # First version
                )
                self.stdout.write(self.style.SUCCESS(f'Created version for story: {story.title}'))
                
                # Create episodes for this version
                num_episodes = random.randint(1, 5)
                for i in range(1, num_episodes + 1):
                    episode = Episode.objects.create(
                        version=version,
                        title=f'Episode {i} for {story.title}',
                        content=f'Content for episode {i} of {story.title}. This is sample content.',
                        creator=story.creator
                    )
                    self.stdout.write(self.style.SUCCESS(f'Created episode: {episode.title}'))
                
                # Create a second version for some stories
                if random.random() > 0.7:
                    version2 = Version.objects.create(
                        story=story,
                        version_number='00002'  # Second version
                    )
                    self.stdout.write(self.style.SUCCESS(f'Created second version for story: {story.title}'))
                    
                    # Create episodes for second version
                    num_episodes = random.randint(1, 3)
                    for i in range(1, num_episodes + 1):
                        episode = Episode.objects.create(
                            version=version2,
                            title=f'V2 Episode {i} for {story.title}',
                            content=f'Content for version 2, episode {i} of {story.title}. This is updated content.',
                            creator=story.creator
                        )
                        self.stdout.write(self.style.SUCCESS(f'Created episode for version 2: {episode.title}'))
            else:
                self.stdout.write(f'Versions already exist for story: {story.title}')
        
        # Create some reports
        if stories and users:
            for i in range(5):
                story = random.choice(stories)
                reporter = random.choice(users)
                
                # Avoid self-reporting
                if reporter != story.creator:
                    if not StoryReport.objects.filter(story=story, reported_by=reporter).exists():
                        report = StoryReport.objects.create(
                            story=story,
                            reported_by=reporter,
                            reason=f'Sample report reason {i+1}'
                        )
                        self.stdout.write(self.style.SUCCESS(f'Created story report by {reporter.username}'))
        
        # Create some episode reports
        episodes = Episode.objects.all()
        if episodes and users:
            for i in range(3):
                episode = random.choice(episodes)
                reporter = random.choice(users)
                
                # Avoid self-reporting
                if reporter != episode.creator:
                    if not EpisodeReport.objects.filter(episode=episode, reported_by=reporter).exists():
                        report = EpisodeReport.objects.create(
                            episode=episode,
                            reported_by=reporter,
                            reason=f'Sample episode report reason {i+1}'
                        )
                        self.stdout.write(self.style.SUCCESS(f'Created episode report by {reporter.username}'))
        
        # Create user relationships (followers)
        if users:
            for user in users:
                # Each user follows 1-3 other users
                for i in range(random.randint(1, 3)):
                    user_to_follow = random.choice(users)
                    if user != user_to_follow and user_to_follow not in user.profile.following.all():
                        user.profile.following.add(user_to_follow)
                        self.stdout.write(f'{user.username} is now following {user_to_follow.username}')
        
        self.stdout.write(self.style.SUCCESS('Database population completed!'))