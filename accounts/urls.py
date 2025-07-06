from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, CurrentUserView, ProfileView,
    FollowUserView, UnfollowUserView, FollowedStoriesView, FavoriteStoriesView,
    AddToFavoritesView, RemoveFromFavoritesView, ChangeUserRoleView, CreateUserView,
    AssignUserToSubadminView, RemoveUserAssignmentView, ListAssignedUsersView,
    CreateOrganizationView, ListOrganizationsView, OrganizationDetailView,
    RemoveMemberFromOrganizationView,
    DeleteUserView, SubadminDeleteUserView, DeleteOrganizationView,AddMultipleMembersToOrganizationView,
    UserActivityStatsView,
)

from storyapp.views import AdminEpisodeReviewView, ApproveEpisodeView, RejectEpisodeView
from rest_framework.authtoken.views import obtain_auth_token
from .views import password_reset_request, verify_reset_code,reset_password

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/', obtain_auth_token, name='token_obtain'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('follow/<int:user_id>/', FollowUserView.as_view(), name='follow_user'),
    path('unfollow/<int:user_id>/', UnfollowUserView.as_view(), name='unfollow_user'),
    path('followed-stories/', FollowedStoriesView.as_view(), name='followed_stories'),
    path('favorite-stories/', FavoriteStoriesView.as_view(), name='favorite_stories'),
    path('favorite/<int:story_id>/', AddToFavoritesView.as_view(), name='add_to_favorites'),
    path('unfavorite/<int:story_id>/', RemoveFromFavoritesView.as_view(), name='remove_from_favorites'),
    path('users/<int:user_id>/change-role/', ChangeUserRoleView.as_view(), name='change_user_role'),
    path('users/create/', CreateUserView.as_view(), name='create_user'),
    path('users/<int:user_id>/assign/<int:subadmin_id>/', AssignUserToSubadminView.as_view(), name='assign_user_to_subadmin'),
    path('users/<int:user_id>/unassign/', RemoveUserAssignmentView.as_view(), name='remove_user_assignment'),
    path('subadmins/<int:subadmin_id>/users/', ListAssignedUsersView.as_view(), name='list_assigned_users'),
    path('assignments/', ListAssignedUsersView.as_view(), name='list_all_assignments'),
    
    # Organization management
    path('organizations/', CreateOrganizationView.as_view(), name='create_organization'),
    path('organizations/list/', ListOrganizationsView.as_view(), name='list_organizations'),
    path('organizations/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
    #path('organizations/<int:organization_id>/add-member/<int:user_id>/', AddMemberToOrganizationView.as_view(), name='add_member_to_organization'),
    # Add this URL pattern to your urlpatterns list
    path('organizations/<int:organization_id>/add-member/', AddMultipleMembersToOrganizationView.as_view(), name='add_multiple_members_to_organization'),
    path('organizations/<int:organization_id>/remove-member/<int:user_id>/', RemoveMemberFromOrganizationView.as_view(), name='remove_member_from_organization'),
    path('stats/user-activity/', UserActivityStatsView.as_view(), name='user_activity_stats'),
    path('admin/episodes/pending-review/', AdminEpisodeReviewView.as_view(), name='admin-episode-review'),
    path('admin/episodes/<int:episode_id>/approve/', ApproveEpisodeView.as_view(), name='approve-episode'),
    path('admin/episodes/<int:episode_id>/reject/', RejectEpisodeView.as_view(), name='reject-episode'),
    
    # User deletion endpoints
    path('admin/users/<int:user_id>/delete/', DeleteUserView.as_view(), name='admin_delete_user'),
    path('subadmin/users/<int:user_id>/delete/', SubadminDeleteUserView.as_view(), name='subadmin_delete_user'),
    
    # Organization deletion endpoint
    path('organizations/<int:organization_id>/delete/', DeleteOrganizationView.as_view(), name='delete_organization'),
    path('password-reset/', password_reset_request, name='password_reset'),
    path('verify-reset-code/', verify_reset_code, name='verify_reset_code'),
    path('reset-password/', reset_password, name='reset_password'),
]
