from rest_framework import generics, permissions, status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .serializers import UserRegisterSerializer, UserSerializer, ProfileSerializer
from .models import Profile
from storyapp.models import Story
from storyapp.serializers import StorySerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer

class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user = authenticate(username=request.data['username'], password=request.data['password'])
        if not user:
            return Response({'error': 'Invalid credentials'}, status=400)
        login(request, user)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        request.user.auth_token.delete()
        logout(request)
        return Response(status=status.HTTP_200_OK)

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.profile

class FollowUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            user_to_follow = User.objects.get(id=user_id)
            if user_to_follow == request.user:
                return Response({'error': 'You cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)
            
            request.user.profile.following.add(user_to_follow)
            return Response({'detail': f'You are now following {user_to_follow.username}'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class UnfollowUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            user_to_unfollow = User.objects.get(id=user_id)
            request.user.profile.following.remove(user_to_unfollow)
            return Response({'detail': f'You have unfollowed {user_to_unfollow.username}'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class FollowedStoriesView(generics.ListAPIView):
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Story.objects.filter(followed_by=self.request.user)

class FavoriteStoriesView(generics.ListAPIView):
    serializer_class = StorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.request.user.profile.favorite_stories.all()

class AddToFavoritesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, story_id):
        try:
            story = Story.objects.get(id=story_id)
            request.user.profile.favorite_stories.add(story)
            return Response({'detail': 'Added to favorites'}, status=status.HTTP_200_OK)
        except Story.DoesNotExist:
            return Response({'error': 'Story not found'}, status=status.HTTP_404_NOT_FOUND)

class RemoveFromFavoritesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, story_id):
        try:
            story = Story.objects.get(id=story_id)
            request.user.profile.favorite_stories.remove(story)
            return Response({'detail': 'Removed from favorites'}, status=status.HTTP_200_OK)
        except Story.DoesNotExist:
            return Response({'error': 'Story not found'}, status=status.HTTP_404_NOT_FOUND)
