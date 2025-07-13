from django.urls import path
from .views import (
    OAuthRedirectView, OAuthCallbackView, CredentialsSignInView,
    MagicLinkView, MagicLinkVerifyView, UserListView,
    AppListCreateView, ApiKeyListView, OAuthConfigView
)

urlpatterns = [
    # Authentication APIs
    path('auth/<str:provider>/<str:app_id>', OAuthRedirectView.as_view(), name='oauth_redirect'),
    path('auth/callback/<str:provider>/<str:app_id>', OAuthCallbackView.as_view(), name='oauth_callback'),
    path('auth/credentials/<str:app_id>', CredentialsSignInView.as_view(), name='credentials_signin'),
    path('auth/magic-link/<str:app_id>', MagicLinkView.as_view(), name='magic_link'),
    path('auth/verify/<str:app_id>', MagicLinkVerifyView.as_view(), name='magic_link_verify'),
    # User Management API
    path('users/<str:app_id>', UserListView.as_view(), name='user_list'),
    # App Management
    path('apps/', AppListCreateView.as_view(), name='app_list_create'),
    # API Key Management
    path('apps/<str:app_id>/api-keys', ApiKeyListView.as_view(), name='api_key_list'),
    # OAuth Config Management
    path('apps/<str:app_id>/oauth-configs', OAuthConfigView.as_view(), name='oauth_config'),
]