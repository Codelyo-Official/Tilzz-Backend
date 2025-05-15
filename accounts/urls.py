from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, CurrentUserView, ProfileView,
    FollowUserView, UnfollowUserView, FollowedStoriesView, FavoriteStoriesView,
    AddToFavoritesView, RemoveFromFavoritesView, ChangeUserRoleView, CreateUserView,
    AssignUserToSubadminView, RemoveUserAssignmentView, ListAssignedUsersView,
    CreateOrganizationView, ListOrganizationsView, OrganizationDetailView,
    AddMemberToOrganizationView, RemoveMemberFromOrganizationView
)
from rest_framework.authtoken.views import obtain_auth_token

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
    path('organizations/<int:organization_id>/add-member/<int:user_id>/', AddMemberToOrganizationView.as_view(), name='add_member_to_organization'),
    path('organizations/<int:organization_id>/remove-member/<int:user_id>/', RemoveMemberFromOrganizationView.as_view(), name='remove_member_from_organization'),
]
