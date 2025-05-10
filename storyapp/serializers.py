from rest_framework import serializers
from .models import Story, Version, Episode, StoryReport, Organization
from django.contrib.auth.models import User

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

class EpisodeSerializer(serializers.ModelSerializer):
    has_next = serializers.SerializerMethodField()
    has_previous = serializers.SerializerMethodField()
    
    class Meta:
        model = Episode
        fields = ['id', 'title', 'content', 'version', 'created_at', 'has_next', 'has_previous']
    
    def get_has_next(self, obj):
        # Check if there's a next episode in the same version
        next_episode = Episode.objects.filter(
            version=obj.version,
            created_at__gt=obj.created_at
        ).order_by('created_at').first()
        return next_episode is not None
    
    def get_has_previous(self, obj):
        # Check if there's a previous episode in the same version
        previous_episode = Episode.objects.filter(
            version=obj.version,
            created_at__lt=obj.created_at
        ).order_by('-created_at').first()
        return previous_episode is not None

class VersionSerializer(serializers.ModelSerializer):
    has_next = serializers.SerializerMethodField()
    has_previous = serializers.SerializerMethodField()
    
    class Meta:
        model = Version
        fields = ['id', 'story', 'version_number', 'created_at', 'has_next', 'has_previous']
    
    def get_has_next(self, obj):
        # Check if there's a next version in the same story
        next_version = Version.objects.filter(
            story=obj.story,
            version_number__gt=obj.version_number
        ).order_by('version_number').first()
        return next_version is not None
    
    def get_has_previous(self, obj):
        # Check if there's a previous version in the same story
        previous_version = Version.objects.filter(
            story=obj.story,
            version_number__lt=obj.version_number
        ).order_by('-version_number').first()
        return previous_version is not None
    episodes = EpisodeSerializer(many=True, read_only=True)

    class Meta:
        model = Version
        fields = '__all__'

class StorySerializer(serializers.ModelSerializer):
    versions = VersionSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source='liked_by.count', read_only=True)
    followers_count = serializers.IntegerField(source='followed_by.count', read_only=True)
    creator_username = serializers.ReadOnlyField(source='creator.username')
    cover_image = serializers.ImageField(required=False)

    class Meta:
        model = Story
        fields = '__all__'
        read_only_fields = ['creator']

class StoryReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.ReadOnlyField(source='reported_by.username')
    story_title = serializers.ReadOnlyField(source='story.title')
    
    class Meta:
        model = StoryReport
        fields = '__all__'
        read_only_fields = ['reported_by']
