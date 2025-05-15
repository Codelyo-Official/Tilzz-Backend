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
    next_id = serializers.SerializerMethodField()
    previous_id = serializers.SerializerMethodField()
    has_other_version = serializers.SerializerMethodField()
    other_version_id = serializers.SerializerMethodField()
    previous_version = serializers.SerializerMethodField()
    next_version = serializers.SerializerMethodField()
    creator_username = serializers.ReadOnlyField(source='creator.username')
    
    class Meta:
        model = Episode
        fields = ['id', 'title', 'content', 'version', 'parent_episode', 'created_at', 
                 'has_next', 'has_previous', 'next_id', 'previous_id', 
                 'has_other_version', 'other_version_id', 'previous_version', 'next_version',
                 'creator', 'creator_username']
        read_only_fields = ['version', 'parent_episode', 'creator']
    
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
        
    def get_next_id(self, obj):
        # Check if there's a next episode in the same version
        next_episode = Episode.objects.filter(
            version=obj.version,
            created_at__gt=obj.created_at
        ).order_by('created_at').first()
        return next_episode.id if next_episode else None
    
    def get_previous_id(self, obj):
        # Check if there's a previous episode in the same version
        previous_episode = Episode.objects.filter(
            version=obj.version,
            created_at__lt=obj.created_at
        ).order_by('-created_at').first()
        return previous_episode.id if previous_episode else None
    
    def get_has_other_version(self, obj):
        # Check if this episode has a parent or children in other versions
        if obj.parent_episode:
            return True
        
        # Check if this episode has child episodes in other versions
        has_children = Episode.objects.filter(parent_episode=obj.id).exists()
        return has_children
    
    def get_other_version_id(self, obj):
        # If this episode has a parent, return the parent's ID
        if obj.parent_episode:
            return obj.parent_episode.id
        
        # Otherwise, return the ID of the first child episode (if any)
        child_episode = Episode.objects.filter(parent_episode=obj.id).first()
        return child_episode.id if child_episode else None
    
    def get_previous_version(self, obj):
        # If this episode has a parent, that's the previous version
        if obj.parent_episode:
            return {
                'id': obj.parent_episode.id,
                'title': obj.parent_episode.title,
                'version': obj.parent_episode.version.id,
                'version_number': obj.parent_episode.version.version_number
            }
        return None
    
    def get_next_version(self, obj):
        # Find child episodes (newer versions of this episode)
        child_episode = Episode.objects.filter(parent_episode=obj.id).first()
        if child_episode:
            return {
                'id': child_episode.id,
                'title': child_episode.title,
                'version': child_episode.version.id,
                'version_number': child_episode.version.version_number
            }
        return None

class VersionSerializer(serializers.ModelSerializer):
    has_next = serializers.SerializerMethodField()
    has_previous = serializers.SerializerMethodField()
    next_id = serializers.SerializerMethodField()
    previous_id = serializers.SerializerMethodField()
    episodes = EpisodeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Version
        fields = ['id', 'story', 'version_number', 'created_at', 'has_next', 'has_previous', 'next_id', 'previous_id', 'episodes']
    
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
    
    def get_next_id(self, obj):
        try:
            # No need to convert to int first, string comparison will work with padded numbers
            next_version = Version.objects.filter(
                story=obj.story,
                version_number__gt=obj.version_number
            ).order_by('version_number').first()
            return next_version.id if next_version else None
        except Exception:
            # Handle any unexpected errors
            return None
    
    def get_previous_id(self, obj):
        previous_version = Version.objects.filter(
            story=obj.story,
            version_number__lt=obj.version_number
        ).order_by('-version_number').first()
        return previous_version.id if previous_version else None

class StorySerializer(serializers.ModelSerializer):
    versions = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(source='liked_by.count', read_only=True)
    followers_count = serializers.IntegerField(source='followed_by.count', read_only=True)
    creator_username = serializers.ReadOnlyField(source='creator.username')
    cover_image = serializers.ImageField(required=False)

    class Meta:
        model = Story
        fields = '__all__'
        read_only_fields = ['creator']
    
    def get_versions(self, obj):
        # Check if we should return all versions or just the root version
        request = self.context.get('request')
        if not request:
            # Default to root version if no request context
            root_version = obj.versions.order_by('version_number').first()
            if root_version:
                serializer = VersionSerializer(root_version, context=self.context)
                return [serializer.data]
            return []
            
        # Check if a specific version is requested (check both 'version' and 'versions' parameters)
        version_param = request.query_params.get('version') or request.query_params.get('versions')
        if version_param:
            # First try to get the specific version by id
            try:
                version_id = int(version_param)
                specific_version = obj.versions.filter(id=version_id).first()
                if specific_version:
                    serializer = VersionSerializer(specific_version, context=self.context)
                    return [serializer.data]
            except (ValueError, TypeError):
                pass
            
            # If not found by id, try by version_number (padded)
            try:
                # Pad the version number for consistent comparison
                padded_version = str(int(version_param)).zfill(5)
                specific_version = obj.versions.filter(version_number=padded_version).first()
                if specific_version:
                    serializer = VersionSerializer(specific_version, context=self.context)
                    return [serializer.data]
            except (ValueError, TypeError):
                # If version_param is not a valid integer, try exact match
                specific_version = obj.versions.filter(version_number=version_param).first()
                if specific_version:
                    serializer = VersionSerializer(specific_version, context=self.context)
                    return [serializer.data]
            
            # If version not found, return empty list
            return []
        
        # Check if all versions are requested
        if request.query_params.get('all_versions', '').lower() == 'true':
            # Return all versions
            serializer = VersionSerializer(obj.versions.all(), many=True, context=self.context)
            return serializer.data
        
        # Default: return root version
        root_version = obj.versions.order_by('version_number').first()
        if root_version:
            serializer = VersionSerializer(root_version, context=self.context)
            return [serializer.data]
        return []

class StoryReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.ReadOnlyField(source='reported_by.username')
    story_title = serializers.ReadOnlyField(source='story.title')
    
    class Meta:
        model = StoryReport
        fields = '__all__'
        read_only_fields = ['reported_by']
