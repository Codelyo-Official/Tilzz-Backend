from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StoryViewSet, VersionViewSet, EpisodeViewSet, StoryReportViewSet,
    PublicStoryListView, PublicStoryDetailView, OrganizationViewSet,
    AdminUserListView, MakeSubadminView, QuarantinedStoriesView,
    StoryReportsView, ApproveStoryView, RejectStoryView,
    SubadminUserListView, AddUserToOrganizationView, AdminStoryManagementView,
    SubadminStoryListView, SubadminStoryVisibilityView, EpisodeReportsView, EpisodeReportViewSet,
    SubmitEpisodeForApprovalView,
    QuarantinedEpisodesListView,StoriesWithReportedEpisodesView,UserEpisodesWithReportedStoriesView,PendingEpisodesView,
    DeleteEpisodeView,AdminEpisodeReviewView,ApproveEpisodeView,RejectEpisodeView,AdminDeleteStoryView,AdminPendingEpisodesView,CategoryViewSet,StoryInviteViewSet
)

router = DefaultRouter()
router.register(r'stories', StoryViewSet, basename='story')
router.register(r'versions', VersionViewSet)
#router.register(r'episodes', EpisodeViewSet)
router.register(r'episodes', EpisodeViewSet, basename='episode')
router.register(r'episode-reports', EpisodeReportViewSet)  # Fix: remove 'views.' prefix
router.register('organizations', OrganizationViewSet)
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'story-invites', StoryInviteViewSet, basename='story-invite')

from django.urls import path
from . import views
from .views import UserQuarantinedEpisodesView

urlpatterns = [
    path('', include(router.urls)),
    
    # Public endpoints
    path('public/stories/', PublicStoryListView.as_view(), name='public-stories'),
    path('public/stories/<int:pk>/', PublicStoryDetailView.as_view(), name='public-story-detail'),
    
    # Admin endpoints
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/make-subadmin/', MakeSubadminView.as_view(), name='make-subadmin'),
    path('admin/quarantined-stories/', QuarantinedStoriesView.as_view(), name='quarantined-stories'),
    path('admin/quarantined-stories/<int:story_id>/reports/', StoryReportsView.as_view(), name='story-reports'),
    path('admin/quarantined-stories/<int:story_id>/approve/', ApproveStoryView.as_view(), name='approve-story'),
    path('admin/quarantined-stories/<int:story_id>/reject/', RejectStoryView.as_view(), name='reject-story'),
    
    # Subadmin endpoints
    path('admin/subadmin/users/', SubadminUserListView.as_view(), name='subadmin-users'),
    path('admin/subadmin/users/<int:user_id>/add_to_organization/', AddUserToOrganizationView.as_view(), name='add-to-organization'),
    # New URL pattern for adding members to specific organization
    path('accounts/organizations/<int:org_id>/add-member/<int:user_id>/', AddUserToOrganizationView.as_view(), name='add-member-to-organization'),
    # New URL pattern for adding multiple members to specific organization
    path('accounts/organizations/<int:org_id>/add-member/', AddUserToOrganizationView.as_view(), name='add-members-to-organization'),
    path('admin/subadmin/stories/', SubadminStoryListView.as_view(), name='subadmin-stories'),
    path('admin/subadmin/stories/<int:story_id>/visibility/', SubadminStoryVisibilityView.as_view(), name='subadmin_change_story_visibility'),
    # Add nested URLs for episodes
    path('<int:story_id>/episodes/', EpisodeViewSet.as_view({'post': 'create', 'get': 'by_story'})),
    path('episodes/<int:pk>/branch/', EpisodeViewSet.as_view({'post': 'branch'}), name='episode-branch'),
    # Add these to your existing urlpatterns
    path('admin/stories/', AdminStoryManagementView.as_view(), name='admin_stories_list'),
    path('admin/stories/<int:story_id>/', AdminStoryManagementView.as_view(), name='admin_story_detail'),
    path('admin/stories/<int:story_id>/visibility/', AdminStoryManagementView.as_view(), name='admin_change_story_visibility'),
    path('episodes/<int:episode_id>/reports/', EpisodeReportsView.as_view(), name='episode-reports'),  # Fix: remove 'views.' prefix
    # Add these to urlpatterns
    path('api/quarantined-episodes/', UserEpisodesWithReportedStoriesView.as_view(), name='quarantined-episodes'),
    #path('api/my-quarantined-episodes/', UserQuarantinedEpisodesView.as_view(), name='my-quarantined-episodes'),
    path('api/admin/pending-episodes/', PendingEpisodesView.as_view(), name='pending-episodes'),
    path('api/episodes/<int:episode_id>/submit-for-approval/', SubmitEpisodeForApprovalView.as_view(), name='submit-episode-for-approval'),
    path('api/stories/with-reported-episodes/', StoriesWithReportedEpisodesView.as_view(), name='stories-with-reported-episodes'),
    # Episode deletion and admin review endpoints
    path('episodes/<int:episode_id>/delete/', DeleteEpisodeView.as_view(), name='delete-episode'),
    path('admin/episodes/pending-review/', AdminEpisodeReviewView.as_view(), name='admin-episode-review'),
    path('admin/episodes/<int:episode_id>/approve/', ApproveEpisodeView.as_view(), name='approve-episode'),
    path('admin/episodes/<int:episode_id>/reject/', RejectEpisodeView.as_view(), name='reject-episode'),
    # Admin story deletion endpoint
    path('admin/stories/<int:story_id>/delete/', AdminDeleteStoryView.as_view(), name='admin-delete-story'),
    
]
