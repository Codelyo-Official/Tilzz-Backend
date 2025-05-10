from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, CurrentUserView, ProfileView,
    FollowUserView, UnfollowUserView, FollowedStoriesView, FavoriteStoriesView,
    AddToFavoritesView, RemoveFromFavoritesView
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
]
