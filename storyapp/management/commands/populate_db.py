from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile, Organization
from storyapp.models import Story, Version, Episode, StoryReport, EpisodeReport
from django.utils import timezone
import random
from django.core.files.uploadedfile import SimpleUploadedFile
import os
from faker import Faker
import logging
from django.db import transaction

class Command(BaseCommand):
    help = 'Populates the database with sample data'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake = Faker()
        self.logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of regular users to create'
        )
        parser.add_argument(
            '--stories',
            type=int,
            default=15,
            help='Number of stories to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Populating database...')
        
        # Clear existing data if requested
        if options['clear']:
            self._clear_data()
            
        # Create users
        admin_user = self._create_admin_user()
        subadmins = self._create_subadmin_users()
        users = self._create_regular_users(options['users'], subadmins)
        
        # Create organizations
        organizations = self._create_organizations(subadmins, admin_user, users)
        
        # Create stories and related content
        stories = self._create_stories(options['stories'], users, admin_user)
        self._create_versions_and_episodes(stories)
        self._create_reports(stories, users)
        self._create_user_relationships(users)
        
        self.stdout.write(self.style.SUCCESS('Database population completed!'))

    def _clear_data(self):
        """Clear existing data before populating"""
        self.stdout.write('Clearing existing data...')
        # Only delete data created by this script, not all data
        EpisodeReport.objects.all().delete()
        StoryReport.objects.all().delete()
        Episode.objects.all().delete()
        Version.objects.all().delete()
        Story.objects.all().delete()
        # Don't delete users or profiles as they might be created by other means
        self.stdout.write(self.style.SUCCESS('Data cleared successfully'))

    def _create_admin_user(self):
        """Create admin user if it doesn't exist"""
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpassword'
            )
            admin_user.profile.role = 'admin'
            admin_user.profile.bio = self.fake.paragraph()
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.username}'))
        else:
            admin_user = User.objects.get(username='admin')
            self.stdout.write('Admin user already exists')
        return admin_user

    def _create_subadmin_users(self, count=2):
        """Create subadmin users"""
        subadmins = []
        for i in range(1, count + 1):
            username = f'subadmin{i}'
            if not User.objects.filter(username=username).exists():
                subadmin = User.objects.create_user(
                    username=username,
                    email=f'subadmin{i}@example.com',
                    password='subadminpassword'
                )
                subadmin.profile.role = 'subadmin'
                subadmin.profile.bio = self.fake.paragraph()
                subadmin.profile.save()
                subadmins.append(subadmin)
                self.stdout.write(self.style.SUCCESS(f'Created subadmin: {subadmin.username}'))
            else:
                subadmins.append(User.objects.get(username=username))
                self.stdout.write(f'Subadmin {username} already exists')
        return subadmins

    def _create_regular_users(self, count, subadmins):
        """Create regular users"""
        users = []
        for i in range(1, count + 1):
            username = f'user{i}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'user{i}@example.com',
                    password='userpassword'
                )
                user.profile.bio = self.fake.paragraph()
                
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
        return users

    def _create_organizations(self, subadmins, admin_user, users, count=3):
        """Create organizations and add members"""
        organizations = []
        for i in range(1, count + 1):
            org_name = f'Organization {i}'
            if not Organization.objects.filter(name=org_name).exists():
                org = Organization.objects.create(
                    name=org_name,
                    description=self.fake.paragraph(),
                    created_by=random.choice(subadmins) if subadmins else admin_user
                )
                
                # Add members to organization
                member_count = min(len(users), random.randint(3, 6))
                selected_members = random.sample(users, member_count) if users else []
                for member in selected_members:
                    org.members.add(member)
                
                organizations.append(org)
                self.stdout.write(self.style.SUCCESS(f'Created organization: {org.name} with {member_count} members'))
            else:
                organizations.append(Organization.objects.get(name=org_name))
                self.stdout.write(f'Organization {org_name} already exists')
        return organizations

    def _create_stories(self, count, users, admin_user):
        """Create stories with random attributes"""
        stories = []
        visibility_choices = ['public', 'private', 'followers']
        
        for i in range(1, count + 1):
            title = f'{self.fake.catch_phrase()} - Story {i}'
            if not Story.objects.filter(title=title).exists():
                creator = random.choice(users) if users else admin_user
                
                story = Story.objects.create(
                    title=title,
                    description=self.fake.paragraph(nb_sentences=5),
                    creator=creator,
                    visibility=random.choice(visibility_choices)
                )
                
                # Add likes and followers with more variability
                like_count = random.randint(0, min(8, len(users)))
                if users and like_count > 0:
                    likers = random.sample(users, like_count)
                    for liker in likers:
                        if liker != creator:  # Avoid self-liking
                            story.liked_by.add(liker)
                
                follower_count = random.randint(0, min(5, len(users)))
                if users and follower_count > 0:
                    followers = random.sample(users, follower_count)
                    for follower in followers:
                        if follower != creator:  # Avoid self-following
                            story.followed_by.add(follower)
                
                stories.append(story)
                self.stdout.write(self.style.SUCCESS(
                    f'Created story: {story.title} with {like_count} likes and {follower_count} followers'
                ))
            else:
                stories.append(Story.objects.get(title=title))
                self.stdout.write(f'Story with title similar to {title} already exists')
        return stories

    def _create_versions_and_episodes(self, stories):
        """Create versions and episodes for stories"""
        for story in stories:
            # Create at least one version for each story
            if not Version.objects.filter(story=story).exists():
                version = Version.objects.create(
                    story=story,
                    version_number='00001'  # First version
                )
                self.stdout.write(self.style.SUCCESS(f'Created version for story: {story.title}'))
                
                # Create episodes for this version with more realistic content
                num_episodes = random.randint(1, 5)
                for i in range(1, num_episodes + 1):
                    episode = Episode.objects.create(
                        version=version,
                        title=f'Episode {i}: {self.fake.sentence()}',
                        content=self.fake.paragraphs(nb=random.randint(3, 8)),
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
                    
                    # Create episodes for second version with parent relationship
                    first_version_episodes = Episode.objects.filter(version=version)
                    num_episodes = min(len(first_version_episodes), random.randint(1, 3))
                    
                    for i in range(num_episodes):
                        parent_episode = first_version_episodes[i] if i < len(first_version_episodes) else None
                        
                        episode = Episode.objects.create(
                            version=version2,
                            title=f'V2 Episode {i+1}: {self.fake.sentence()}',
                            content=self.fake.paragraphs(nb=random.randint(3, 8)),
                            creator=story.creator,
                            parent_episode=parent_episode
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f'Created episode for version 2: {episode.title} with parent: {parent_episode.title if parent_episode else "None"}'
                        ))
            else:
                self.stdout.write(f'Versions already exist for story: {story.title}')

    def _create_reports(self, stories, users):
        """Create story and episode reports"""
        # Create some story reports
        if stories and users:
            for i in range(min(5, len(stories))):
                story = random.choice(stories)
                available_reporters = [user for user in users if user != story.creator]
                
                if available_reporters:
                    reporter = random.choice(available_reporters)
                    
                    if not StoryReport.objects.filter(story=story, reported_by=reporter).exists():
                        report = StoryReport.objects.create(
                            story=story,
                            reported_by=reporter,
                            reason=self.fake.paragraph(),
                            status=random.choice(['pending', 'approved', 'rejected'])
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f'Created story report by {reporter.username} for "{story.title}" with status: {report.status}'
                        ))
        
        # Create some episode reports
        episodes = Episode.objects.all()
        if episodes and users:
            for i in range(min(5, len(episodes))):
                episode = random.choice(episodes)
                available_reporters = [user for user in users if user != episode.creator]
                
                if available_reporters:
                    reporter = random.choice(available_reporters)
                    
                    if not EpisodeReport.objects.filter(episode=episode, reported_by=reporter).exists():
                        report = EpisodeReport.objects.create(
                            episode=episode,
                            reported_by=reporter,
                            reason=self.fake.paragraph(),
                            status=random.choice(['pending', 'approved', 'rejected'])
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f'Created episode report by {reporter.username} for "{episode.title}" with status: {report.status}'
                        ))
                        
                        # Check if this triggered a status change
                        if episode.status == Episode.QUARANTINED:
                            self.stdout.write(self.style.WARNING(
                                f'Episode "{episode.title}" has been quarantined due to multiple reports'
                            ))

    def _create_user_relationships(self, users):
        """Create user relationships (followers)"""
        if users:
            for user in users:
                # Each user follows 1-3 other users
                available_users = [u for u in users if u != user and u not in user.profile.following.all()]
                
                if available_users:
                    follow_count = min(len(available_users), random.randint(1, 3))
                    users_to_follow = random.sample(available_users, follow_count)
                    
                    for user_to_follow in users_to_follow:
                        user.profile.following.add(user_to_follow)
                        self.stdout.write(f'{user.username} is now following {user_to_follow.username}')