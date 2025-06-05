from rest_framework import generics, permissions, status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Profile, Organization
from .serializers import OrganizationSerializer
from .serializers import UserRegisterSerializer, UserSerializer, ProfileSerializer
from .models import Profile
from storyapp.models import Story
from storyapp.serializers import StorySerializer

from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.mail import send_mail
from datetime import datetime, timedelta
from django.db.models.functions import TruncDate
from django.db.models import Count, DateField
import random


class UserActivityStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date 30 days ago
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Get signups by day
        signups = User.objects.filter(
            date_joined__gte=thirty_days_ago
        ).annotate(
            date=TruncDate('date_joined', output_field=DateField())
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Get logins by day (assuming you're using Django's last_login field)
        logins = User.objects.filter(
            last_login__gte=thirty_days_ago
        ).annotate(
            date=TruncDate('last_login', output_field=DateField())
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Format response
        response_data = {
            'signups': list(signups),
            'logins': list(logins)
        }
        
        return Response(response_data)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create token for the new user
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        
        # Return user data along with token
        user_serializer = UserSerializer(user)
        
        return Response({
            'token': token.key,
            'user': user_serializer.data
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user = authenticate(username=request.data['username'], password=request.data['password'])
        if not user:
            return Response({'error': 'Invalid credentials'}, status=400)
        token, _ = Token.objects.get_or_create(user=user)
        
        # Get user data to return along with token
        from accounts.serializers import UserSerializer
        user_data = UserSerializer(user).data
        
        # Combine token and user data in response
        response_data = {
            'token': token.key,
            'user': user_data
        }
        
        return Response(response_data)

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

class ChangeUserRoleView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        # Check if the requesting user is an admin
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Only admins can change user roles'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
            role = request.data.get('role')
            
            # Validate the role
            if role not in ['user', 'subadmin', 'admin']:
                return Response({'error': 'Invalid role. Choose from: user, subadmin, admin'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Set the role and save
            user.profile.role = role
            user.profile.save()
            
            return Response({
                'detail': f'User {user.username} role changed to {role}',
                'user_id': user.id,
                'username': user.username,
                'role': role
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class CreateUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if the requesting user is an admin or subadmin
        if not hasattr(request.user, 'profile') or request.user.profile.role not in ['admin', 'subadmin']:
            return Response({'error': 'Only admins and subadmins can create users'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Get user details from request
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role', 'user')  # Default to 'user' if not specified
        
        # Validate required fields
        if not all([username, email, password]):
            return Response({'error': 'Username, email, and password are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # If the user is a subadmin, they can only create regular users
        if request.user.profile.role == 'subadmin' and role != 'user':
            return Response({'error': 'Subadmins can only create regular users'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Validate role
        if role not in ['user', 'subadmin', 'admin']:
            return Response({'error': 'Invalid role. Choose from: user, subadmin, admin'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            return Response({'error': f'User with username {username} already exists'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': f'User with email {email} already exists'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Create the user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Set the role
            user.profile.role = role
            
            # If the creator is a subadmin, automatically assign the new user to them
            if request.user.profile.role == 'subadmin':
                user.profile.assigned_to = request.user
            
            user.profile.save()
            
            # Return user data
            user_serializer = UserSerializer(user)
            return Response({
                'message': f'User {username} created successfully with role: {role}',
                'user': user_serializer.data,
                'assigned_to': request.user.username if request.user.profile.role == 'subadmin' else None
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': f'Error creating user: {str(e)}'}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssignUserToSubadminView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id, subadmin_id):
        # Check if the requesting user is an admin
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Only admins can assign users to subadmins'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get the user to be assigned
            user = User.objects.get(id=user_id)
            
            # Get the subadmin
            subadmin = User.objects.get(id=subadmin_id)
            
            # Check if the subadmin is actually a subadmin
            if not hasattr(subadmin, 'profile') or subadmin.profile.role != 'subadmin':
                return Response({'error': 'The specified user is not a subadmin'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Assign the user to the subadmin
            user.profile.assigned_to = subadmin
            user.profile.save()
            
            return Response({
                'message': f'User {user.username} has been assigned to subadmin {subadmin.username}',
                'user_id': user.id,
                'username': user.username,
                'subadmin_id': subadmin.id,
                'subadmin_username': subadmin.username
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'User or subadmin not found'}, 
                           status=status.HTTP_404_NOT_FOUND)

class RemoveUserAssignmentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        # Check if the requesting user is an admin
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Only admins can remove user assignments'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get the user
            user = User.objects.get(id=user_id)
            
            # Check if the user is assigned to a subadmin
            if not user.profile.assigned_to:
                return Response({'error': 'This user is not assigned to any subadmin'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Store the subadmin info for the response
            subadmin_username = user.profile.assigned_to.username
            subadmin_id = user.profile.assigned_to.id
            
            # Remove the assignment
            user.profile.assigned_to = None
            user.profile.save()
            
            return Response({
                'message': f'User {user.username} has been unassigned from subadmin {subadmin_username}',
                'user_id': user.id,
                'username': user.username,
                'previous_subadmin_id': subadmin_id,
                'previous_subadmin_username': subadmin_username
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, 
                           status=status.HTTP_404_NOT_FOUND)

class ListAssignedUsersView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, subadmin_id=None):
        # Check if the requesting user is an admin or the subadmin in question
        is_admin = hasattr(request.user, 'profile') and request.user.profile.role == 'admin'
        is_target_subadmin = subadmin_id and str(request.user.id) == str(subadmin_id)
        
        if not (is_admin or is_target_subadmin):
            return Response({'error': 'You do not have permission to view these assignments'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # If subadmin_id is provided, get users assigned to that subadmin
        if subadmin_id:
            try:
                subadmin = User.objects.get(id=subadmin_id)
                
                # Check if the user is actually a subadmin
                if not hasattr(subadmin, 'profile') or subadmin.profile.role != 'subadmin':
                    return Response({'error': 'The specified user is not a subadmin'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                
                # Get all users assigned to this subadmin
                assigned_users = User.objects.filter(profile__assigned_to=subadmin)
                
                # Serialize the users
                from accounts.serializers import UserSerializer
                serializer = UserSerializer(assigned_users, many=True)
                
                return Response({
                    'subadmin_id': subadmin.id,
                    'subadmin_username': subadmin.username,
                    'assigned_users': serializer.data
                })
                
            except User.DoesNotExist:
                return Response({'error': 'Subadmin not found'}, 
                               status=status.HTTP_404_NOT_FOUND)
        
        # If no subadmin_id is provided and the user is an admin, get all assignments
        elif is_admin:
            # Get all subadmins
            subadmins = User.objects.filter(profile__role='subadmin')
            
            # For each subadmin, get their assigned users
            assignments = []
            for subadmin in subadmins:
                assigned_users = User.objects.filter(profile__assigned_to=subadmin)
                
                # Serialize the users
                from accounts.serializers import UserSerializer
                user_serializer = UserSerializer(assigned_users, many=True)
                
                assignments.append({
                    'subadmin_id': subadmin.id,
                    'subadmin_username': subadmin.username,
                    'assigned_users': user_serializer.data
                })
            
            return Response(assignments)
        
        # If the user is neither an admin nor the specified subadmin
        else:
            return Response({'error': 'Invalid request'}, 
                           status=status.HTTP_400_BAD_REQUEST)

class CreateOrganizationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if the requesting user is an admin or subadmin
        if not hasattr(request.user, 'profile') or request.user.profile.role not in ['admin', 'subadmin']:
            return Response({'error': 'Only admins and subadmins can create organizations'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Get organization details from request
        name = request.data.get('name')
        description = request.data.get('description', '')
        
        # Validate required fields
        if not name:
            return Response({'error': 'Organization name is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Check if organization with this name already exists
        if Organization.objects.filter(name=name).exists():
            return Response({'error': f'Organization with name {name} already exists'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Create the organization
        try:
            organization = Organization.objects.create(
                name=name,
                description=description,
                created_by=request.user
            )
            
            # Add the creator as a member
            organization.members.add(request.user)
            
            # Return organization data
            serializer = OrganizationSerializer(organization)
            return Response({
                'message': f'Organization {name} created successfully',
                'organization': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': f'Error creating organization: {str(e)}'}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ListOrganizationsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # If user is admin, return all organizations
        if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
            organizations = Organization.objects.all()
        # If user is subadmin, return organizations created by them
        elif hasattr(request.user, 'profile') and request.user.profile.role == 'subadmin':
            organizations = Organization.objects.filter(created_by=request.user)
        # If user is regular user, return organizations they are a member of
        else:
            organizations = request.user.organizations.all()
        
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)

class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            organization = Organization.objects.get(pk=pk)
            
            # Check if user has permission to view this organization
            if self.request.user.profile.role == 'admin':
                return organization
            elif self.request.user.profile.role == 'subadmin' and organization.created_by == self.request.user:
                return organization
            elif organization.members.filter(id=self.request.user.id).exists():
                return organization
            else:
                raise PermissionError("You don't have permission to view this organization")
                
        except Organization.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        try:
            organization = self.get_object(pk)
            serializer = OrganizationSerializer(organization)
            
            # Get members
            members_serializer = UserSerializer(organization.members.all(), many=True)
            
            return Response({
                'organization': serializer.data,
                'members': members_serializer.data
            })
        except PermissionError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Http404:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, pk):
        try:
            organization = self.get_object(pk)
            
            # Only creator or admin can update organization
            if not (request.user.profile.role == 'admin' or organization.created_by == request.user):
                return Response({'error': 'Only the creator or an admin can update this organization'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # Update fields
            if 'name' in request.data:
                organization.name = request.data['name']
            if 'description' in request.data:
                organization.description = request.data['description']
            
            organization.save()
            
            serializer = OrganizationSerializer(organization)
            return Response(serializer.data)
            
        except PermissionError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Http404:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, pk):
        try:
            organization = self.get_object(pk)
            
            # Only creator or admin can delete organization
            if not (request.user.profile.role == 'admin' or organization.created_by == request.user):
                return Response({'error': 'Only the creator or an admin can delete this organization'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            organization.delete()
            return Response({'message': 'Organization deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
            
        except PermissionError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Http404:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

class IsSubadmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and hasattr(request.user, 'profile') and (
            request.user.profile.role in ['subadmin', 'admin'] or request.user.organizations.exists()
        )

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


class AddMultipleMembersToOrganizationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, organization_id):
        try:
            organization = Organization.objects.get(id=organization_id)
            
            # Check if the requesting user is an admin or the organization creator
            is_admin = request.user.profile.role == 'admin'
            is_creator = organization.created_by == request.user
            
            if not (is_admin or is_creator):
                return Response({'error': 'You do not have permission to add members to this organization'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # Get user IDs from request
            user_ids_str = request.data.get('user_ids', '')
            if not user_ids_str:
                return Response({'error': 'No user IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse user IDs
            try:
                user_ids = [int(id.strip()) for id in str(user_ids_str).split(',')]
            except ValueError:
                return Response({'error': 'Invalid user_ids format. Provide comma-separated values'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Add users to organization
            added_users = []
            not_found_users = []
            
            for uid in user_ids:
                try:
                    user_to_add = User.objects.get(id=uid)
                    
                    # If the requesting user is a subadmin, check if the user is assigned to them
                    if request.user.profile.role == 'subadmin' and not is_admin:
                        is_assigned = user_to_add.profile.assigned_to == request.user
                        
                        if not is_assigned:
                            continue  # Skip users not assigned to this subadmin
                    
                    organization.members.add(user_to_add)
                    added_users.append({
                        'id': user_to_add.id,
                        'username': user_to_add.username
                    })
                except User.DoesNotExist:
                    not_found_users.append(uid)
            
            return Response({
                'message': f'{len(added_users)} users added to organization {organization.name}',
                'organization_id': organization.id,
                'organization_name': organization.name,
                'added_users': added_users,
                'not_found_users': not_found_users
            }, status=status.HTTP_200_OK)
            
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

class RemoveMemberFromOrganizationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, organization_id, user_id):
        try:
            organization = Organization.objects.get(id=organization_id)
            
            # Check if the requesting user is an admin or the organization creator
            is_admin = request.user.profile.role == 'admin'
            is_creator = organization.created_by == request.user
            
            if not (is_admin or is_creator):
                return Response({'error': 'You do not have permission to remove members from this organization'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # Get the user to remove
            try:
                user_to_remove = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is a member
            if not organization.members.filter(id=user_to_remove.id).exists():
                return Response({'error': 'This user is not a member of the organization'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # If the requesting user is a subadmin, check if the user is assigned to them or created by them
            if request.user.profile.role == 'subadmin' and not is_admin:
                # Check if user was created by this subadmin or assigned to this subadmin
                is_assigned = user_to_remove.profile.assigned_to == request.user
                
                if not is_assigned:
                    return Response({
                        'error': 'You can only remove users who are assigned to you'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Remove the user from the organization
            organization.members.remove(user_to_remove)
            
            return Response({
                'message': f'User {user_to_remove.username} removed from organization {organization.name}',
                'organization_id': organization.id,
                'organization_name': organization.name,
                'user_id': user_to_remove.id,
                'username': user_to_remove.username
            }, status=status.HTTP_200_OK)
            
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

class SubadminDeleteUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, user_id):
        # Check if the requesting user is a subadmin or admin
        if not hasattr(request.user, 'profile') or request.user.profile.role not in ['subadmin', 'admin']:
            return Response({'error': 'Only subadmins and admins can access this endpoint'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
            
            # Don't allow subadmins to delete themselves
            if user == request.user:
                return Response({'error': 'You cannot delete your own account'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # If subadmin, check if the user was created by them
            if request.user.profile.role == 'subadmin':
                # Check if the user is assigned to this subadmin
                if not hasattr(user, 'profile') or user.profile.assigned_to != request.user:
                    return Response({'error': 'You can only delete users assigned to you'}, 
                                  status=status.HTTP_403_FORBIDDEN)
            
            username = user.username
            user.delete()
            
            return Response({
                'detail': f'User {username} has been deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class DeleteOrganizationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, organization_id):
        try:
            organization = Organization.objects.get(id=organization_id)
            
            # Check permissions:
            # 1. Admin can delete any organization
            # 2. Subadmin can only delete organizations they created
            is_admin = hasattr(request.user, 'profile') and request.user.profile.role == 'admin'
            is_creator = organization.created_by == request.user
            
            if not (is_admin or is_creator):
                return Response({'error': 'You do not have permission to delete this organization'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            org_name = organization.name
            organization.delete()
            
            return Response({
                'detail': f'Organization "{org_name}" has been deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, user_id):
        # Check if the requesting user is an admin
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return Response({'error': 'Only admins can delete users'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
            
            # Don't allow admins to delete themselves
            if user == request.user:
                return Response({'error': 'You cannot delete your own account'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            username = user.username
            user.delete()
            
            return Response({
                'detail': f'User {username} has been deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

# Password reset request view
@csrf_exempt
@api_view(['POST'])
def password_reset_request(request):
    email = request.data.get('email')
    try:
        user = User.objects.get(email=email)
        # Generate 6-digit code
        reset_code = str(random.randint(100000, 999999))
        # Store code in user's profile (or session)
        profile = user.profile
        profile.reset_code = reset_code
        profile.save()
        
        # Send email with reset code
        send_mail(
            'Password Reset Code',
            f'Your password reset code is: {reset_code}',
            'noreply@yourdomain.com',
            [email],
            fail_silently=False,
        )
        return Response({'detail': 'Reset code sent to your email'}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'No user with that email address'}, status=status.HTTP_404_NOT_FOUND)

@csrf_exempt
@api_view(['POST'])
def verify_reset_code(request):
    email = request.data.get('email')
    code = request.data.get('code')
    new_password = request.data.get('new_password')
    
    try:
        user = User.objects.get(email=email)
        if user.profile.reset_code == code:
            user.set_password(new_password)
            user.save()
            # Clear reset code
            user.profile.reset_code = None
            user.profile.save()
            return Response({'detail': 'Password updated successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid reset code'}, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        return Response({'error': 'Invalid email'}, status=status.HTTP_404_NOT_FOUND)