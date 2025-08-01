"""
URL configuration for auth_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from auth_service.views import home, user_list_dashboard, add_user_dashboard, delete_app, CustomLoginView, CustomSignupView, dashboard, create_app_dashboard, app_details, add_auth_config, test_oauth_config, oauth_callback
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('auth_api.urls')),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('signup/', CustomSignupView.as_view(), name='signup'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', dashboard, name='dashboard'), # Root dashboard
    path('dashboard/app/<str:app_id>/', app_details, name='app_details'),
    path('dashboard/app/<str:app_id>/add_oauth_config', add_auth_config, name='add_auth_config'),
    path('dashboard/app/<str:app_id>/test_oauth_config/<int:config_id>', test_oauth_config, name='test_oauth_config'),
    path('oauth/callback', oauth_callback, name='oauth_callback'),
    path('dashboard/<str:app_id>/users', user_list_dashboard, name='user_list_dashboard'),
    path('dashboard/<str:app_id>/users/add', add_user_dashboard, name='add_user_dashboard'),
    path('dashboard/create_app/', create_app_dashboard, name='create_app_dashboard'),
    path('apps/<str:app_id>/delete/', delete_app, name='delete_app'),
]
