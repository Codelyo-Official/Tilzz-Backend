from rest_framework import serializers
from .models import Story, Version, Episode, StoryReport, Organization,EpisodeReport
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Story, Episode, Version, StoryReport, EpisodeReport,Category,StoryInvite
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
    creator_admin = serializers.SerializerMethodField()
    is_reported = serializers.SerializerMethodField()
    story_title = serializers.SerializerMethodField()
    story_id = serializers.SerializerMethodField()
    reports_count = serializers.SerializerMethodField()
    reporting_users = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    class Meta:
        model = Episode
        fields = ['id', 'title', 'content', 'version', 'parent_episode', 'created_at', 
                 'has_next', 'has_previous', 'next_id', 'previous_id', 
                 'has_other_version', 'other_version_id', 'previous_version', 'next_version',
                 'creator', 'creator_username', 'creator_admin', 'is_reported', 'story_title', 
                 'story_id', 'status', 'reports_count','reporting_users','likes_count', 'is_liked']
        read_only_fields = ['version', 'parent_episode', 'creator']
    def get_likes_count(self, obj):
        return obj.liked_by.count()
        
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.liked_by.filter(id=request.user.id).exists()
        return False
    def get_reporting_users(self, obj):
        return list(obj.reports.values_list('reported_by__username', flat=True))
    def get_story_title(self, obj):
        return obj.version.story.title
    
    def get_story_id(self, obj):
        return obj.version.story.id
    
    def get_reports_count(self, obj):
        return obj.reports.count()
    
    def get_is_reported(self, obj):
        # Check if this episode has 3 or more reports
        return EpisodeReport.objects.filter(episode=obj).count() >= 3
    
    def get_creator_admin(self, obj):
        # Get the creator's admin (if assigned to one)
        if hasattr(obj.creator, 'profile') and obj.creator.profile.assigned_to:
            admin = obj.creator.profile.assigned_to
            return {
                'id': admin.id,
                'username': admin.username,
                'role': admin.profile.role if hasattr(admin, 'profile') else None
            }
        return None
    
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
    creator_admin = serializers.SerializerMethodField()
    category = serializers.CharField(required=False, allow_blank=True)
    cover_image = serializers.ImageField(required=False, use_url=True)

    class Meta:
        model = Story
        fields = '__all__'
        read_only_fields = ['creator']
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        if request and rep.get('cover_image'):
            rep['cover_image'] = request.build_absolute_uri(rep['cover_image'])
        return rep
    def create(self, validated_data):
        category_name = validated_data.pop('category', '').strip()
        if category_name:
            category_obj, _ = Category.objects.get_or_create(
                name__iexact=category_name,
                defaults={'name': category_name}
            )
            validated_data['category'] = category_obj
        return super().create(validated_data)
    def update(self, instance, validated_data):
        category_name = validated_data.pop('category', '').strip()
        if category_name:
            category_obj, _ = Category.objects.get_or_create(
                name__iexact=category_name,
                defaults={'name': category_name}
            )
            validated_data['category'] = category_obj
        return super().update(instance, validated_data)
    def get_creator_admin(self, obj):
        # Get the creator's admin (if assigned to one)
        if hasattr(obj.creator, 'profile') and obj.creator.profile.assigned_to:
            admin = obj.creator.profile.assigned_to
            return {
                'id': admin.id,
                'username': admin.username,
                'role': admin.profile.role if hasattr(admin, 'profile') else None
            }
        return None
    
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

class EpisodeReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.ReadOnlyField(source='reported_by.username')
    episode_title = serializers.ReadOnlyField(source='episode.title')
    reports_count = serializers.SerializerMethodField()
    
    
    class Meta:
        model = EpisodeReport
        fields = ['id', 'episode', 'reported_by', 'reporter_username', 'episode_title', 'reason', 'created_at', 'status', 'reports_count']
        read_only_fields = ['reported_by']

    def get_reports_count(self, obj):
        return obj.episode.reports.count()

    def get_reporting_users(self, obj):
        return list(obj.reports.values_list('reported_by__username', flat=True))
    
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']



from rest_framework import serializers
from .models import StoryInvite
from .serializers import StorySerializer

class StoryInviteSerializer(serializers.ModelSerializer):
    invited_by_username = serializers.ReadOnlyField(source='invited_by.username')
    story_data = StorySerializer(source='story', read_only=True)

    class Meta:
        model = StoryInvite
        fields = [
            'id',
            'story',
            'story_data',
            'invited_email',
            'invited_by',
            'invited_by_username',
            'invited_user',
            'created_at',
            'accepted'
        ]
        read_only_fields = ['invited_by', 'invited_user', 'accepted']

    def validate_invited_email(self, value):
        if self.context['request'].user.email.lower() == value.lower():
            raise serializers.ValidationError("You cannot invite yourself.")
        return value

        