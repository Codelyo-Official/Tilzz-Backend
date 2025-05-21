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
    StoryReportSerializer, OrganizationSerializer, EpisodeReportSerializer, EpisodeReport
)
from accounts.serializers import UserSerializer
# Remove the circular import - don't import from .views
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class IsCreatorOrReadOnly(IsAuthenticatedOrReadOnly):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return obj.creator == request.user

class IsSubadmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and hasattr(request.user, 'profile') and (
            request.user.profile.role in ['subadmin', 'admin'] or request.user.organizations.exists()
        )

class IsAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and hasattr(request.user, 'profile') and request.user.profile.role == 'admin'

class PublicStoryListView(generics.ListAPIView):
    serializer_class = StorySerializer
    
    def get_queryset(self):
        user = self.request.user
        #return Story.objects.filter(visibility='public')
        if user.is_authenticated:
            return Story.objects.filter(
                Q(visibility='public') | 
                Q(creator=user) | 
                Q(visibility='quarantined') | 
                Q(visibility='reported')
            )
        return Story.objects.filter(
            Q(visibility='public') | 
            Q(visibility='quarantined') | 
            Q(visibility='reported'
        ))

class PublicStoryDetailView(generics.RetrieveAPIView):
    serializer_class = StorySerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            #return Story.objects.filter(visibility='public')
            return Story.objects.filter(
                Q(visibility='public') | 
                Q(creator=user) | 
                Q(visibility='quarantined') | 
                Q(visibility='r eported')
            )
        return Story.objects.filter(
            Q(visibility='public') | 
            Q(visibility='Quarantined') | 
            Q(visibility='Reported'
        ))

class StoryViewSet(viewsets.ModelViewSet):
    serializer_class = StorySerializer
    permission_classes = [IsCreatorOrReadOnly|IsAdminUser|IsSubadmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # If authenticated, show public stories, user's own stories, and specific visibility statuses
            return Story.objects.filter(
                Q(visibility='public') | 
                Q(creator=user) | 
                Q(visibility='quarantined') | 
                Q(visibility='reported')
            )
        # For non-authenticated users, show public, quarantined, and reported stories
        return Story.objects.filter(
            Q(visibility='public') | 
            Q(visibility='quarantined') | 
            Q(visibility='reported'
        ))
    
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
    #permission_classes = [IsCreatorOrReadOnly|IsAdminUser|IsSubadmin]

    # We no longer need to handle version creation manually
    # The perform_create method can be removed
    
    def perform_create(self, serializer):
        story = get_object_or_404(Story, pk=self.request.data.get('story'))
        '''if story.creator != self.request.user:
            return Response({'error': 'You can only create versions for your own stories'}, status=status.HTTP_403_FORBIDDEN)'''
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
    #permission_classes = [IsCreatorOrReadOnly|IsAdminUser|IsSubadmin]

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
    
    # In the EpisodeViewSet class, modify the branch method
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
        
        # Find the latest episode in the chain that has this parent as its ancestor
        latest_in_chain = parent_episode
        child = Episode.objects.filter(parent_episode=latest_in_chain.id).first()
        while child:
            latest_in_chain = child
            child = Episode.objects.filter(parent_episode=latest_in_chain.id).first()
        
        # Create new episode with the new version and reference to the latest in chain
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            version=new_version,
            parent_episode=latest_in_chain,
            creator=request.user
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def by_story(self, request, story_id=None):
        # Get story_id from URL parameter if provided, otherwise from query params
        story_id = story_id or request.query_params.get('story_id')
        if not story_id:
            return Response({'error': 'story_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        episodes = Episode.objects.filter(version__story_id=story_id)
        
        # Explicitly use the EpisodeSerializer with all fields
        from .serializers import EpisodeSerializer
        serializer = EpisodeSerializer(episodes, many=True, context={'request': request})
        
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

class EpisodeReportViewSet(viewsets.ModelViewSet):
    queryset = EpisodeReport.objects.all()
    serializer_class = EpisodeReportSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Save the report with the current user as reporter
        report = serializer.save(reported_by=self.request.user)
        
        # Check if this report triggered quarantine
        episode = report.episode
        report_count = EpisodeReport.objects.filter(episode=episode).count()
        
        # Add a message to the response
        if report_count >= 3:
            story = episode.version.story
            if story.visibility == 'quarantined':
                self.message = "This episode has been automatically quarantined due to multiple reports."
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if hasattr(self, 'message'):
            response.data['message'] = self.message
        return response
        
        # Check if this episode's story has reached the report threshold
        episode = Episode.objects.get(id=serializer.validated_data['episode'].id)
        story = episode.version.story
        
        # Count total reports for this story (including all episodes)
        story_reports_count = StoryReport.objects.filter(story=story).count()
        
        # Count reports for all episodes in this story
        episode_reports_count = EpisodeReport.objects.filter(
            episode__version__story=story
        ).count()
        
        # If total reports >= 3, mark the story as reported
        if story_reports_count + episode_reports_count >= 3:
            story.visibility = 'reported'  # Make sure 'reported' is a valid choice in your Story model
            story.save()

class StoryReportViewSet(viewsets.ModelViewSet):
    queryset = StoryReport.objects.all()
    serializer_class = StoryReportSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Save the report with the current user as reporter
        serializer.save(reported_by=self.request.user)
        
        # Check if this story has reached the report threshold
        story = serializer.validated_data['story']
        
        # Count total reports for this story
        story_reports_count = StoryReport.objects.filter(story=story).count()
        
        # Count reports for all episodes in this story
        episode_reports_count = EpisodeReport.objects.filter(
            episode__version__story=story
        ).count()
        
        # If total reports >= 3, mark the story as reported
        if story_reports_count + episode_reports_count >= 3:
            story.visibility = Story.REPORTED
            story.save()

# Admin views
# Replace IsAdminUser with IsAdmin in the relevant views

# For example:
class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]  # Changed from IsAdminUser

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

class EpisodeReportsView(generics.ListAPIView):
    serializer_class = EpisodeReportSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        episode_id = self.kwargs.get('episode_id')
        return EpisodeReport.objects.filter(episode_id=episode_id)

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
    
    def post(self, request, user_id=None, org_id=None):
        # Get organization
        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get the first organization the subadmin is a member of
            org = request.user.organizations.first()
            
            if not org:
                return Response({'error': 'You are not a member of any organization'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user has permission for this organization
        if not request.user.organizations.filter(id=org.id).exists() and request.user.profile.role != 'admin':
            return Response({'error': 'You do not have permission for this organization'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Handle multiple user IDs
        user_ids = []
        
        # Check if user_id is provided in URL
        if user_id:
            user_ids.append(user_id)
        
        # Check if user_ids are provided in request body
        body_user_ids = request.data.get('user_ids', [])
        if body_user_ids:
            if isinstance(body_user_ids, list):
                user_ids.extend(body_user_ids)
            else:
                # Handle comma-separated string
                try:
                    user_ids.extend([int(id.strip()) for id in str(body_user_ids).split(',')])
                except ValueError:
                    return Response({'error': 'Invalid user_ids format. Provide a list or comma-separated values'}, 
                                   status=status.HTTP_400_BAD_REQUEST)
        
        if not user_ids:
            return Response({'error': 'No user IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add users to organization
        added_users = []
        not_found_users = []
        
        for uid in user_ids:
            try:
                user = User.objects.get(id=uid)
                org.members.add(user)
                added_users.append(user.username)
            except User.DoesNotExist:
                not_found_users.append(uid)
        
        # Prepare response
        response_data = {
            'detail': f'{len(added_users)} users added to {org.name}',
            'added_users': added_users
        }
        
        if not_found_users:
            response_data['not_found_users'] = not_found_users
        
        return Response(response_data, status=status.HTTP_200_OK)

# Admin Story Management Functionality


class AdminStoryManagementView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if the requesting user is an admin
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Only admins can access this endpoint'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Get all stories
        stories = Story.objects.all()
        
        # Serialize the stories
        serializer = StorySerializer(stories, many=True)
        
        return Response(serializer.data)
    
    def put(self, request, story_id):
        # Check if the requesting user is an admin
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Only admins can change story visibility'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get the story
            story = Story.objects.get(id=story_id)
            
            # Get visibility from request
            visibility = request.data.get('visibility')
            
            # Validate visibility
            if visibility not in ['public', 'private', 'followers']:
                return Response({'error': 'Invalid visibility. Choose from: public, private, followers'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Update visibility
            story.visibility = visibility
            story.save()
            
            # Return updated story
            serializer = StorySerializer(story)
            return Response({
                'message': f'Story visibility changed to {visibility}',
                'story': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Story.DoesNotExist:
            return Response({'error': 'Story not found'}, status=status.HTTP_404_NOT_FOUND)

class SubadminStoryVisibilityView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request, story_id):
        # Check if the requesting user is a subadmin
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'subadmin':
            return Response({'error': 'Only subadmins can use this endpoint'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get the story
            story = Story.objects.get(id=story_id)
            
            # Get users assigned to this subadmin
            assigned_users = User.objects.filter(profile__assigned_to=request.user)
            
            # Check if story creator is managed by this subadmin
            if story.creator not in assigned_users:
                return Response({'error': 'You can only modify stories created by users assigned to you'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # Get visibility from request
            visibility = request.data.get('visibility')
            
            # Validate visibility
            if visibility not in ['public', 'private', 'followers']:
                return Response({'error': 'Invalid visibility. Choose from: public, private, followers'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Update visibility
            story.visibility = visibility
            story.save()
            
            # Return updated story
            serializer = StorySerializer(story)
            return Response({
                'message': f'Story visibility changed to {visibility}',
                'story': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Story.DoesNotExist:
            return Response({'error': 'Story not found'}, status=status.HTTP_404_NOT_FOUND)

class SubadminStoryListView(generics.ListAPIView):
    serializer_class = StorySerializer
    permission_classes = [IsSubadmin]
    
    def get_queryset(self):
        user = self.request.user
        
        # Get users in the same organizations as the subadmin
        user_orgs = user.organizations.all()
        org_users = User.objects.filter(organizations__in=user_orgs)
        
        # Get users assigned to this subadmin
        assigned_users = User.objects.filter(profile__assigned_to=user)
        
        # Instead of using the OR operator, use Q objects to combine the conditions
        from django.db.models import Q
        
        # Get all managed users using Q objects
        managed_users = User.objects.filter(
            Q(organizations__in=user_orgs) | 
            Q(profile__assigned_to=user)
        ).distinct()
        
        # Get all stories where either:
        # 1. The creator is one of the managed users, or
        # 2. The story has episodes created by managed users
        return Story.objects.filter(
            Q(creator__in=managed_users) | 
            Q(versions__episodes__creator__in=managed_users)
        ).distinct()

## Step 2: Create the API View
from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Story, Episode, Version
from .serializers import EpisodeSerializer

class UserQuarantinedEpisodesView(generics.ListAPIView):
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        This view returns all quarantined episodes created by the current user
        """
        return Episode.objects.filter(
            creator=self.request.user,
            status=Episode.QUARANTINED
        ).order_by('-created_at')
        
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        episodes = self.filter_queryset(queryset)
        
        # Group episodes by story
        stories_with_episodes = {}
        
        for episode in episodes:
            story = episode.version.story
            story_id = story.id
            
            if story_id not in stories_with_episodes:
                # Serialize the story
                story_serializer = StorySerializer(story)
                stories_with_episodes[story_id] = {
                    'story': story_serializer.data,
                    'episodes': []
                }
            
            # Serialize the episode
            episode_serializer = self.get_serializer(episode)
            stories_with_episodes[story_id]['episodes'].append(episode_serializer.data)
        
        # Convert dictionary to list for response
        response_data = list(stories_with_episodes.values())
        
        return Response(response_data)

class QuarantinedEpisodesListView(generics.ListAPIView):
    serializer_class = EpisodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Get all quarantined stories
        quarantined_stories = Story.objects.filter(visibility='quarantined')
        
        # Get all versions from quarantined stories
        versions = Version.objects.filter(story__in=quarantined_stories)
        
        # Get all episodes from these versions
        episodes = Episode.objects.filter(version__in=versions)
        
        return episodes

class SubmitEpisodeForApprovalView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, episode_id):
        try:
            episode = Episode.objects.get(id=episode_id)
            
            # Check if the user is the creator of the episode
            if episode.creator != request.user:
                return Response({'error': 'You can only submit your own episodes for approval'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # Check if the episode is in a state that can be submitted
            if episode.status != Episode.QUARANTINED:
                return Response({'error': 'Only quarantined episodes can be submitted for approval'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Update the status to pending
            episode.status = Episode.PENDING
            episode.save()
            EpisodeReport.objects.filter(episode=episode, status='approved').update(status='pending')

            return Response({'detail': 'Episode submitted for approval successfully'}, status=status.HTTP_200_OK)
        except Episode.DoesNotExist:
            return Response({'error': 'Episode not found'}, status=status.HTTP_404_NOT_FOUND)

class AdminEpisodeReviewView(generics.ListAPIView):
    serializer_class = EpisodeReportSerializer
    permission_classes = [IsAdmin|IsSubadmin]  
    # Use a custom permission class that combines both
    def get_queryset(self):
        # Get all episode reports with status 'pending'
        return EpisodeReport.objects.filter(status='pending')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Group episodes by story
        stories_dict = {}
        processed_episodes = set()  # Track processed episode IDs
        
        for report_data in serializer.data:
            episode_id = report_data.get('episode')
            
            # Skip if we've already processed this episode
            if episode_id in processed_episodes:
                continue
                
            processed_episodes.add(episode_id)  # Mark as processed
            
            if episode_id:
                try:
                    # Get the episode object
                    episode = Episode.objects.get(id=episode_id)
                    # Get the version and story
                    version = episode.version
                    story = version.story
                    
                    # Create episode data with all details
                    episode_data = {
                        'id': episode.id,
                        'title': episode.title,
                        'content': episode.content,
                        'version': version.id,
                        'parent_episode': episode.parent_episode.id if episode.parent_episode else None,
                        'created_at': episode.created_at,
                        'has_next': False,
                        'has_previous': False,
                        'next_id': None,
                        'previous_id': None,
                        'has_other_version': False,
                        'other_version_id': None,
                        'previous_version': None,
                        'next_version': None,
                        'creator': episode.creator.id if episode.creator else None,
                        'creator_username': episode.creator.username if episode.creator else None,
                        'creator_admin': None,
                        'is_reported': True,
                        'story_title': story.title,
                        'story_id': story.id,
                        'status': episode.status,
                        'reports_count': EpisodeReport.objects.filter(episode=episode).count()
                    }
                    
                    # Initialize story if not exists
                    if story.id not in stories_dict:
                        stories_dict[story.id] = {
                            'id': story.id,
                            'title': story.title,
                            'description': story.description,
                            'visibility': story.visibility,
                            'created_at': story.created_at,
                            'cover_image': story.cover_image.url if story.cover_image else None,
                            'creator': {
                                'id': story.creator.id,
                                'username': story.creator.username
                            } if story.creator else None,
                            'versions': {}
                        }
                    
                    # Initialize version if not exists
                    if version.id not in stories_dict[story.id]['versions']:
                        stories_dict[story.id]['versions'][version.id] = {
                            'id': version.id,
                            'story': story.id,
                            'version_number': version.version_number,
                            'created_at': version.created_at,
                            'has_next': False,
                            'has_previous': False,
                            'next_id': None,
                            'previous_id': None,
                            'episodes': []
                        }
                    
                    # Add episode to version
                    stories_dict[story.id]['versions'][version.id]['episodes'].append(episode_data)
                    
                except (Episode.DoesNotExist, Story.DoesNotExist):
                    continue
        
        # Now add episodes with status 'deleted'
        deleted_episodes = Episode.objects.filter(status=Episode.DELETED)
        
        for episode in deleted_episodes:
            # Skip if we've already processed this episode
            if episode.id in processed_episodes:
                continue
                
            processed_episodes.add(episode.id)  # Mark as processed
            
            try:
                # Get the version and story
                version = episode.version
                story = version.story
                
                # Create episode data with all details
                episode_data = {
                    'id': episode.id,
                    'title': episode.title,
                    'content': episode.content,
                    'version': version.id,
                    'parent_episode': episode.parent_episode.id if episode.parent_episode else None,
                    'created_at': episode.created_at,
                    'has_next': False,
                    'has_previous': False,
                    'next_id': None,
                    'previous_id': None,
                    'has_other_version': False,
                    'other_version_id': None,
                    'previous_version': None,
                    'next_version': None,
                    'creator': episode.creator.id if episode.creator else None,
                    'creator_username': episode.creator.username if episode.creator else None,
                    'creator_admin': None,
                    'is_reported': False,  # Not reported, just deleted
                    'story_title': story.title,
                    'story_id': story.id,
                    'status': episode.status,
                    'reports_count': 0  # No reports for deleted episodes
                }
                
                # Initialize story if not exists
                if story.id not in stories_dict:
                    stories_dict[story.id] = {
                        'id': story.id,
                        'title': story.title,
                        'description': story.description,
                        'visibility': story.visibility,
                        'created_at': story.created_at,
                        'cover_image': story.cover_image.url if story.cover_image else None,
                        'creator': {
                            'id': story.creator.id,
                            'username': story.creator.username
                        } if story.creator else None,
                        'versions': {}
                    }
                
                # Initialize version if not exists
                if version.id not in stories_dict[story.id]['versions']:
                    stories_dict[story.id]['versions'][version.id] = {
                        'id': version.id,
                        'story': story.id,
                        'version_number': version.version_number,
                        'created_at': version.created_at,
                        'has_next': False,
                        'has_previous': False,
                        'next_id': None,
                        'previous_id': None,
                        'episodes': []
                    }
                
                # Add episode to version
                stories_dict[story.id]['versions'][version.id]['episodes'].append(episode_data)
                
            except (Story.DoesNotExist):
                continue
        
        # Convert the nested dictionary to the desired format
        result = []
        for story_id, story_data in stories_dict.items():
            # Convert versions dict to list
            versions_list = []
            for version_id, version_data in story_data['versions'].items():
                versions_list.append({
                    'id': version_data['id'],
                    'story': version_data['story'],
                    'version_number': version_data['version_number'],
                    'created_at': version_data['created_at'],
                    'has_next': version_data['has_next'],
                    'has_previous': version_data['has_previous'],
                    'next_id': version_data['next_id'],
                    'previous_id': version_data['previous_id'],
                    'episodes': version_data['episodes']
                })
            
            # Add versions list to story
            story_data['versions'] = versions_list
            # Remove the versions dictionary
            result.append(story_data)
        
        return Response(result)

class AdminPendingEpisodesView(generics.ListAPIView):
    serializer_class = EpisodeSerializer
    permission_classes = [IsAdmin|IsSubadmin]  
    
    def get_queryset(self):
        # Get all episode reports with status 'pending'
        return EpisodeReport.objects.filter(status='pending')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Group episodes by story
        stories_dict = {}
        
        for report_data in serializer.data:
            episode_id = report_data.get('episode')
            if episode_id:
                try:
                    # Get the episode object
                    episode = Episode.objects.get(id=episode_id)
                    # Get the version and story
                    version = episode.version
                    story = version.story
                    
                    # Create episode data with all details
                    episode_data = {
                        'id': episode.id,
                        'title': episode.title,
                        'content': episode.content,
                        'version': version.id,
                        'parent_episode': episode.parent_episode.id if episode.parent_episode else None,
                        'created_at': episode.created_at,
                        'has_next': False,  # Will be calculated later if needed
                        'has_previous': False,  # Will be calculated later if needed
                        'next_id': None,
                        'previous_id': None,
                        'has_other_version': False,
                        'other_version_id': None,
                        'previous_version': None,
                        'next_version': None,
                        'creator': episode.creator.id if episode.creator else None,
                        'creator_username': episode.creator.username if episode.creator else None,
                        'creator_admin': None,
                        'is_reported': True,  # Since it's in a report
                        'story_title': story.title,
                        'story_id': story.id,
                        'status': episode.status,
                        'reports_count': EpisodeReport.objects.filter(episode=episode).count()
                    }
                    
                    # Initialize story if not exists
                    if story.id not in stories_dict:
                        stories_dict[story.id] = {
                            'id': story.id,
                            'title': story.title,
                            'description': story.description,
                            'visibility': story.visibility,
                            'created_at': story.created_at,
                            'creator': {
                                'id': story.creator.id,
                                'username': story.creator.username
                            } if story.creator else None,
                            'versions': {}
                        }
                    
                    # Initialize version if not exists
                    if version.id not in stories_dict[story.id]['versions']:
                        stories_dict[story.id]['versions'][version.id] = {
                            'id': version.id,
                            'story': story.id,
                            'version_number': version.version_number,
                            'created_at': version.created_at,
                            'has_next': False,
                            'has_previous': False,
                            'next_id': None,
                            'previous_id': None,
                            'episodes': []
                        }
                    
                    # Add episode to version
                    stories_dict[story.id]['versions'][version.id]['episodes'].append(episode_data)
                    
                except (Episode.DoesNotExist, Story.DoesNotExist):
                    continue
        
        # Convert the nested dictionary to the desired format
        result = []
        for story_id, story_data in stories_dict.items():
            # Convert versions dict to list
            versions_list = []
            for version_id, version_data in story_data['versions'].items():
                versions_list.append({
                    'id': version_data['id'],
                    'story': version_data['story'],
                    'version_number': version_data['version_number'],
                    'created_at': version_data['created_at'],
                    'has_next': version_data['has_next'],
                    'has_previous': version_data['has_previous'],
                    'next_id': version_data['next_id'],
                    'previous_id': version_data['previous_id'],
                    'episodes': version_data['episodes']
                })
            
            # Add versions list to story
            story_data['versions'] = versions_list
            # Remove the versions dictionary
            result.append(story_data)
        
        return Response(result)

class DeleteEpisodeView(generics.UpdateAPIView):
    """
    Instead of actually deleting an episode, this endpoint changes its status to 'pending'
    so an admin can review it before permanent deletion.
    """
    permission_classes = [IsAuthenticated]
    queryset = Episode.objects.all()
    serializer_class = EpisodeSerializer
    lookup_url_kwarg = 'episode_id'
    
    def update(self, request, *args, **kwargs):
        episode = self.get_object()
        
        # Check if the user is the creator of the episode
        if episode.creator != request.user and not request.user.is_staff:
            return Response(
                {"error": "You don't have permission to delete this episode"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Change status to pending instead of deleting
        episode.status = Episode.DELETED
        episode.save()
        
        return Response(
            {"message": "Episode sent for admin review before deletion"}, 
            status=status.HTTP_200_OK
        )

class ApproveEpisodeView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request, episode_id):
        try:
            # Look for episode with either PENDING or DELETED status
            episode = Episode.objects.get(
                id=episode_id, 
                status__in=[Episode.PENDING, Episode.DELETED]
            )
            episode.status = Episode.PUBLIC
            episode.save()
            
            # Delete all reports for this episode
            EpisodeReport.objects.filter(episode=episode).delete()

            return Response({'detail': 'Episode approved and made public'}, status=status.HTTP_200_OK)
        except Episode.DoesNotExist:
            return Response({'error': 'Episode not found or not in a state that can be approved'}, status=status.HTTP_404_NOT_FOUND)

class RejectEpisodeView(APIView):
    permission_classes = [IsAdmin]
    
    def post(self, request, episode_id):
        try:
            episode = Episode.objects.get(id=episode_id, status=Episode.PENDING)
            
            # Keep the episode quarantined
            episode.status = Episode.QUARANTINED
            episode.save()
            
            # Mark all reports as approved
            EpisodeReport.objects.filter(episode=episode, status='pending').update(status='approved')
            
            return Response({'detail': 'Episode rejected and kept quarantined'}, status=status.HTTP_200_OK)
        except Episode.DoesNotExist:
            return Response({'error': 'Pending episode not found'}, status=status.HTTP_404_NOT_FOUND)

class StoriesWithReportedEpisodesView(generics.ListAPIView):
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # No need to get stories here, we'll be filtering by user's episodes
        return Story.objects.filter(visibility='quarantined')
    
    def list(self, request, *args, **kwargs):
        # Get all quarantined episodes created by the current user
        user_quarantined_episodes = Episode.objects.filter(
            creator=self.request.user,
            version__story__visibility='quarantined'
        ).select_related('version__story').distinct()
        
        # Group episodes by story
        stories_with_episodes = {}
        for episode in user_quarantined_episodes:
            story = episode.version.story
            if story.id not in stories_with_episodes:
                # Serialize the story
                story_serializer = self.get_serializer(story)
                stories_with_episodes[story.id] = {
                    'story': story_serializer.data,
                    'episodes': []
                }
            
            # Serialize the episode and add to the story's episodes list
            episode_serializer = EpisodeSerializer(episode)
            stories_with_episodes[story.id]['episodes'].append(episode_serializer.data)
        
        # Convert the dictionary to a list for the response
        response_data = list(stories_with_episodes.values())
        
        return Response(response_data)

class QuarantinedStoriesWithEpisodesView(generics.ListAPIView):
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Story.objects.filter(visibility='quarantined')
    
    def list(self, request, *args, **kwargs):
        # Get all quarantined stories
        quarantined_stories = self.get_queryset()
        
        # Prepare response data
        response_data = []
        
        for story in quarantined_stories:
            # Serialize the story
            story_serializer = self.get_serializer(story)
            
            # Get all episodes for this story
            episodes = Episode.objects.filter(
                version__story=story
            ).select_related('version')
            
            # Serialize the episodes
            episode_serializer = EpisodeSerializer(episodes, many=True)
            
            # Add to response data
            response_data.append({
                'story': story_serializer.data,
                'episodes': episode_serializer.data
            })
        
        return Response(response_data)

class UserEpisodesWithReportedStoriesView(generics.ListAPIView):
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        This view returns all episodes created by the current user
        from stories that have at least one quarantined episode
        """
        # First find stories that have quarantined episodes by this user
        stories_with_quarantined_episodes = Story.objects.filter(
            versions__episodes__status=Episode.QUARANTINED,
            versions__episodes__creator=self.request.user
        ).distinct()
        
        # Then get all episodes by the current user from those stories
        return Episode.objects.filter(
            creator=self.request.user,
            version__story__in=stories_with_quarantined_episodes
        ).select_related('version__story', 'creator')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        episodes = self.filter_queryset(queryset)
        
        # Group episodes by story
        stories_with_episodes = {}
        
        for episode in episodes:
            story = episode.version.story
            story_id = story.id
            
            if story_id not in stories_with_episodes:
                # Serialize the story
                story_serializer = StorySerializer(story)
                stories_with_episodes[story_id] = {
                    'story': story_serializer.data,
                    'quarantined_episodes': [],
                }
            
            # Serialize the episode
            episode_serializer = self.get_serializer(episode)
            
            # Add to appropriate list based on status
            if episode.status == Episode.QUARANTINED:
                stories_with_episodes[story_id]['quarantined_episodes'].append(episode_serializer.data)
           
        # Convert dictionary to list for response
        response_data = list(stories_with_episodes.values())
        
        return Response(response_data)

class PendingEpisodesView(generics.ListAPIView):
    serializer_class = EpisodeSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return Episode.objects.filter(status=Episode.PENDING).select_related('version__story', 'creator')

class AdminDeleteStoryView(generics.DestroyAPIView):
    """
    Allows admins to permanently delete a story
    """
    permission_classes = [IsAdminUser|IsSubadmin]
    queryset = Story.objects.all()
    lookup_url_kwarg = 'story_id'
    
    def destroy(self, request, *args, **kwargs):
        story = self.get_object()
        
        # Permanently delete the story and all related content
        story.delete()
        
        return Response(
            {"message": "Story and all related content permanently deleted"}, 
            status=status.HTTP_204_NO_CONTENT
        )

        