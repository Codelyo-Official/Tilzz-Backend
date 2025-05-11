from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StoryViewSet, VersionViewSet, EpisodeViewSet, StoryReportViewSet,
    PublicStoryListView, PublicStoryDetailView, OrganizationViewSet,
    AdminUserListView, MakeSubadminView, QuarantinedStoriesView,
    StoryReportsView, ApproveStoryView, RejectStoryView,
    SubadminUserListView, AddUserToOrganizationView
)

router = DefaultRouter()
router.register(r'stories', StoryViewSet, basename='story')
router.register(r'versions', VersionViewSet)
router.register(r'episodes', EpisodeViewSet)
router.register('organizations', OrganizationViewSet)

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
    # Add nested URLs for episodes
    path('<int:story_id>/episodes/', EpisodeViewSet.as_view({'post': 'create'})),    # Add URL for branching episodes
    path('episodes/<int:pk>/branch/', EpisodeViewSet.as_view({'post': 'branch'}), name='episode-branch'),
]
