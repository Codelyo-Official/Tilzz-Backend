from rest_framework import viewsets, status, generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, IsAdminUser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from .models import Story, Version, Episode, StoryReport, Organization
from .serializers import (
    StorySerializer, VersionSerializer, EpisodeSerializer, 
    StoryReportSerializer, OrganizationSerializer
)
from accounts.serializers import UserSerializer

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class IsCreatorOrReadOnly(IsAuthenticatedOrReadOnly):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return obj.creator == request.user

class IsSubadmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and hasattr(request.user, 'profile') and request.user.organizations.exists()

class PublicStoryListView(generics.ListAPIView):
    serializer_class = StorySerializer
    
    def get_queryset(self):
        return Story.objects.filter(visibility='public')

class PublicStoryDetailView(generics.RetrieveAPIView):
    serializer_class = StorySerializer
    
    def get_queryset(self):
        return Story.objects.filter(visibility='public')

class StoryViewSet(viewsets.ModelViewSet):
    serializer_class = StorySerializer
    permission_classes = [IsCreatorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # If authenticated, show public stories and user's own stories
            return Story.objects.filter(Q(visibility='public') | Q(creator=user))
        # If not authenticated, only show public stories
        return Story.objects.filter(visibility='public')
    
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        story = self.get_object()
        if request.user in story.liked_by.all():
            return Response({'detail': 'Already liked.'}, status=400)
        story.liked_by.add(request.user)
        return Response({'detail': 'Liked successfully.'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, pk=None):
        story = self.get_object()
        if request.user not in story.liked_by.all():
            return Response({'detail': 'Not liked yet.'}, status=400)
        story.liked_by.remove(request.user)
        return Response({'detail': 'Unliked successfully.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        story = self.get_object()
        if request.user in story.followed_by.all():
            return Response({'detail': 'Already following.'}, status=400)
        story.followed_by.add(request.user)
        return Response({'detail': 'Followed successfully.'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        story = self.get_object()
        if request.user not in story.followed_by.all():
            return Response({'detail': 'Not following yet.'}, status=400)
        story.followed_by.remove(request.user)
        return Response({'detail': 'Unfollowed successfully.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def report(self, request, pk=None):
        story = self.get_object()
        reason = request.data.get('reason')
        if not reason:
            return Response({'error': 'Reason is required.'}, status=400)
        StoryReport.objects.create(story=story, reported_by=request.user, reason=reason)
        return Response({'detail': 'Reported successfully.'})
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_stories(self, request):
        stories = Story.objects.filter(creator=request.user)
        serializer = self.get_serializer(stories, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def feed(self, request):
        # Get stories from users that the current user follows
        following_users = request.user.profile.following.all()
        stories = Story.objects.filter(
            Q(creator__in=following_users, visibility='public') | 
            Q(followed_by=request.user)
        ).distinct().order_by('-created_at')
        serializer = self.get_serializer(stories, many=True)
        return Response(serializer.data)

class VersionViewSet(viewsets.ModelViewSet):
    queryset = Version.objects.all()
    serializer_class = VersionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    # We no longer need to handle version creation manually
    # The perform_create method can be removed
    
    def perform_create(self, serializer):
        story = get_object_or_404(Story, pk=self.request.data.get('story'))
        if story.creator != self.request.user:
            return Response({'error': 'You can only create versions for your own stories'}, status=status.HTTP_403_FORBIDDEN)
        serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def branch(self, request, pk=None):
        version = self.get_object()
        episode_id = request.data.get('episode_id')
        new_title = request.data.get('title')
        new_content = request.data.get('content')
        
        if not all([episode_id, new_title, new_content]):
            return Response({'error': 'episode_id, title and content are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            parent_episode = Episode.objects.get(id=episode_id, version=version)
        except Episode.DoesNotExist:
            return Response({'error': 'Episode not found in this version'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create a new episode with reference to parent version
        new_episode = Episode.objects.create(
            version=version,
            title=new_title,
            content=new_content,
            parent_version=version
        )
        
        serializer = EpisodeSerializer(new_episode)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EpisodeViewSet(viewsets.ModelViewSet):
    queryset = Episode.objects.all()
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def create(self, request, *args, **kwargs):
        # Get story_id from URL if present
        story_id = self.kwargs.get('story_id')
        version_id = request.data.get('version_id')
        
        # Case 1: Creating first episode of a story (auto-create first version)
        if story_id and not version_id:
            story = get_object_or_404(Story, pk=story_id)
            '''if story.creator != request.user:
                return Response({'error': 'You can only create episodes for your own stories'}, 
                               status=status.HTTP_403_FORBIDDEN)'''
            
            # Create first version for this story if it doesn't exist
            version, created = Version.objects.get_or_create(
                story=story,
                defaults={'version_number': 1}  # First version
            )
            
            # Add version_id to request data
            mutable_data = request.data.copy()
            mutable_data['version'] = version.id
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(version=version, creator=request.user)  # Add creator=request.user here
            
        # Case 2: Adding episode to existing version
        elif version_id:
            version = get_object_or_404(Version, pk=version_id)
            '''if version.story.creator != request.user:
                return Response({'error': 'You can only create episodes for your own stories'}, 
                               status=status.HTTP_403_FORBIDDEN)'''
            
            # Add version to request data
            mutable_data = request.data.copy()
            mutable_data['version'] = version.id
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(version=version, creator=request.user)  # Add creator=request.user here
        else:
            return Response({
                'error': 'Invalid request. Please provide either story_id in URL or version_id in body'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def branch(self, request, pk=None):
        parent_episode = self.get_object()
        story = parent_episode.version.story
        
        '''if story.creator != request.user:
            return Response({'error': 'You can only create episodes for your own stories'}, 
                           status=status.HTTP_403_FORBIDDEN)'''
        
        # Get the latest version number for this story
        latest_version = Version.objects.filter(story=story).order_by('-version_number').first()
        new_version_number = 1
        if latest_version:
            new_version_number = latest_version.version_number + str(1)
        
        # Create new version
        new_version = Version.objects.create(
            story=story,
            version_number=new_version_number
        )
        
        # Create new episode with the new version and reference to parent
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            version=new_version,
            parent_episode=parent_episode,
            creator=request.user  # This line sets the creator
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def by_story(self, request):
        story_id = request.query_params.get('story_id')
        if not story_id:
            return Response({'error': 'story_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        episodes = Episode.objects.filter(version__story_id=story_id)
        serializer = self.get_serializer(episodes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def next(self, request, pk=None):
        episode = self.get_object()
        next_episode = Episode.objects.filter(
            version=episode.version,
            created_at__gt=episode.created_at
        ).order_by('created_at').first()
        
        if not next_episode:
            return Response({
                'has_next': False, 
                'next_id': None,
                'next_episode': None
            }, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(next_episode)
        return Response({
            'has_next': True, 
            'next_id': next_episode.id,
            'next_episode': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def previous(self, request, pk=None):
        episode = self.get_object()
        previous_episode = Episode.objects.filter(
            version=episode.version,
            created_at__lt=episode.created_at
        ).order_by('-created_at').first()
        
        if not previous_episode:
            return Response({
                'has_previous': False, 
                'previous_id': None,
                'previous_episode': None
            }, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(previous_episode)
        return Response({
            'has_previous': True, 
            'previous_id': previous_episode.id,
            'previous_episode': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def next_version(self, request, pk=None):
        version = self.get_object()
        next_version = Version.objects.filter(
            story=version.story,
            version_number__gt=version.version_number
        ).order_by('version_number').first()
        
        if not next_version:
            return Response({'has_next': False, 'next_id': None}, status=status.HTTP_200_OK)
        
        return Response({'has_next': True, 'next_id': next_version.id}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def previous_version(self, request, pk=None):
        version = self.get_object()
        previous_version = Version.objects.filter(
            story=version.story,
            version_number__lt=version.version_number
        ).order_by('-version_number').first()
        
        if not previous_version:
            return Response({'has_previous': False, 'previous_id': None}, status=status.HTTP_200_OK)
        
        return Response({'has_previous': True, 'previous_id': previous_version.id}, status=status.HTTP_200_OK)

class StoryReportViewSet(viewsets.ModelViewSet):
    queryset = StoryReport.objects.all()
    serializer_class = StoryReportSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

# Admin views
class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

class MakeSubadminView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            org_id = request.data.get('organization_id')
            
            if not org_id:
                return Response({'error': 'organization_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                org = Organization.objects.get(id=org_id)
                org.members.add(user)
                return Response({'detail': f'{user.username} is now a subadmin for {org.name}'}, status=status.HTTP_200_OK)
            except Organization.DoesNotExist:
                return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdminUser]

class QuarantinedStoriesView(generics.ListAPIView):
    serializer_class = StorySerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return Story.objects.filter(visibility='quarantined')

class StoryReportsView(generics.ListAPIView):
    serializer_class = StoryReportSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        story_id = self.kwargs.get('story_id')
        return StoryReport.objects.filter(story_id=story_id)

class ApproveStoryView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request, story_id):
        try:
            story = Story.objects.get(id=story_id, visibility='quarantined')
            story.visibility = 'public'
            story.save()
            
            # Update all reports for this story
            StoryReport.objects.filter(story=story, status='pending').update(status='rejected')
            
            return Response({'detail': 'Story approved and made public'}, status=status.HTTP_200_OK)
        except Story.DoesNotExist:
            return Response({'error': 'Quarantined story not found'}, status=status.HTTP_404_NOT_FOUND)

class RejectStoryView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request, story_id):
        try:
            story = Story.objects.get(id=story_id, visibility='quarantined')
            story.visibility = 'private'
            story.save()
            
            # Update all reports for this story
            StoryReport.objects.filter(story=story, status='pending').update(status='approved')
            
            return Response({'detail': 'Story rejected and made private'}, status=status.HTTP_200_OK)
        except Story.DoesNotExist:
            return Response({'error': 'Quarantined story not found'}, status=status.HTTP_404_NOT_FOUND)

# Subadmin views
class SubadminUserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsSubadmin]
    
    def get_queryset(self):
        # Get users in the same organizations as the subadmin
        user_orgs = self.request.user.organizations.all()
        return User.objects.filter(organizations__in=user_orgs).distinct()

class AddUserToOrganizationView(APIView):
    permission_classes = [IsSubadmin]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            # Get the first organization the subadmin is a member of
            org = request.user.organizations.first()
            
            if not org:
                return Response({'error': 'You are not a member of any organization'}, status=status.HTTP_400_BAD_REQUEST)
            
            org.members.add(user)
            return Response({'detail': f'{user.username} added to {org.name}'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    