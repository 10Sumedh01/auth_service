from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import authenticate
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from allauth.socialaccount.models import SocialToken
from .models import App, User, ApiKey, OAuthConfig
import uuid
import requests
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
# Custom authentication for API keys
class ApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        key = request.headers.get('Authorization', '').replace('Bearer ', '')
        try:
            api_key = ApiKey.objects.get(key=key, is_active=True)
            return (api_key.app.developer, None)
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed('Invalid or inactive API key')

# OAuth Redirect: Initiates OAuth flow (e.g., GitHub, Google)
class OAuthRedirectView(APIView):
    def get(self, request, provider, app_id):
        try:
            app = App.objects.get(app_id=app_id)
            oauth_config = OAuthConfig.objects.get(app=app, provider=provider)
            redirect_url = (
                f"https://{provider}.com/login/oauth/authorize"
                f"?client_id={oauth_config.client_id}"
                f"&redirect_uri={oauth_config.redirect_uri}"
                f"&scope=user:email"
            )
            return Response({'redirect_url': redirect_url})
        except (App.DoesNotExist, OAuthConfig.DoesNotExist):
            return Response({'error': 'Invalid app or provider'}, status=404)

# OAuth Callback: Handles OAuth callback, stores user, issues JWT
class OAuthCallbackView(APIView):
    def post(self, request, provider, app_id):
        try:
            app = App.objects.get(app_id=app_id)
            oauth_config = OAuthConfig.objects.get(app=app, provider=provider)
            code = request.data.get('code')
            # Exchange code for access token
            token_url = f"https://{provider}.com/login/oauth/access_token"
            response = requests.post(token_url, data={
                'client_id': oauth_config.client_id,
                'client_secret': oauth_config.client_secret,
                'code': code,
                'redirect_uri': oauth_config.redirect_uri,
            }, headers={'Accept': 'application/json'})
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            # Fetch user data (simplified for GitHub)
            user_response = requests.get(
                'https://api.github.com/user',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            user_data = user_response.json()
            user_id = str(user_data.get('id'))
            email = user_data.get('email') or f"{user_id}@github.com"
            name = user_data.get('name', '')

            # Store or update user
            user, _ = User.objects.get_or_create(
                app=app,
                email=email,
                defaults={
                    'user_id': user_id,
                    'name': name,
                    'auth_method': 'oauth',
                }
            )
            user.last_login = timezone.now()
            user.save()

            # Issue JWT
            token = RefreshToken.for_user(app.developer)  # Use developer for token
            token['user_id'] = user.user_id
            token['email'] = email
            token['name'] = name
            return Response({'token': str(token.access_token)})
        except (App.DoesNotExist, OAuthConfig.DoesNotExist):
            return Response({'error': 'Invalid app or provider'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

# Credentials Sign-In: Handles email/password, stores user, issues JWT
class CredentialsSignInView(APIView):
    authentication_classes = [ApiKeyAuthentication]
    def post(self, request, app_id):
        try:
            # Ensure the app from the API key matches the app_id in the URL
            if request.user.app.app_id != app_id:
                return Response({'error': 'API key does not match the app'}, status=403)
            
            app = App.objects.get(app_id=app_id)
            email = request.data.get('email')
            password = request.data.get('password')
            user = authenticate(request, username=email, password=password)
            if user:
                user_obj, _ = User.objects.get_or_create(
                    app=app,
                    email=email,
                    defaults={
                        'user_id': str(user.id),
                        'name': user.get_full_name(),
                        'auth_method': 'credentials',
                    }
                )
                user_obj.last_login = timezone.now()
                user_obj.save()
                token = RefreshToken.for_user(user)
                token['user_id'] = user_obj.user_id
                token['email'] = email
                token['name'] = user_obj.name
                return Response({'token': str(token.access_token)})
            return Response({'error': 'Invalid credentials'}, status=401)
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)

# Magic Link: Sends email link, verifies, issues JWT
class MagicLinkView(APIView):
    def post(self, request, app_id):
        try:
            app = App.objects.get(app_id=app_id)
            email = request.data.get('email')
            user, _ = User.objects.get_or_create(
                app=app,
                email=email,
                defaults={
                    'user_id': str(uuid.uuid4()),
                    'name': '',
                    'auth_method': 'magic_link',
                }
            )
            token = RefreshToken.for_user(app.developer)
            token['user_id'] = user.user_id
            token['email'] = email
            token['name'] = user.name
            link = f"{request.scheme}://{request.get_host()}/api/auth/verify/{app_id}?token={str(token.access_token)}"
            send_mail(
                'Sign In to Your App',
                f'Click to sign in: {link}',
                'from@your-auth-service.com',
                [email],
                fail_silently=False,
            )
            return Response({'success': True})
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)

# Magic Link Verification: Verifies token, updates last_login, returns JWT
class MagicLinkVerifyView(APIView):
    def get(self, request, app_id):
        try:
            token = request.query_params.get('token')
            app = App.objects.get(app_id=app_id)
            # Verify JWT (simplified; use simplejwt's token verification)
            from rest_framework_simplejwt.tokens import AccessToken
            token_obj = AccessToken(token)
            user_id = token_obj['user_id']
            user = User.objects.get(app=app, user_id=user_id)
            user.last_login = timezone.now()
            user.save()
            return Response({'token': str(token)})
        except (App.DoesNotExist, User.DoesNotExist):
            return Response({'error': 'Invalid app or user'}, status=404)
        except Exception:
            return Response({'error': 'Invalid token'}, status=401)

# User List: Fetches users for an app (dashboard and API)
class UserListView(APIView):
    authentication_classes = [ApiKeyAuthentication]
    def get(self, request, app_id):
        try:
            app = App.objects.get(app_id=app_id)
            users = User.objects.filter(app=app).values(
                'user_id', 'email', 'name', 'auth_method', 'last_login', 'created_at'
            )
            return Response(list(users))
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)

# App Management: Create and list apps for developers
class AppListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        apps = App.objects.filter(developer=request.user).values(
            'app_id', 'name', 'created_at'
        )
        return Response(list(apps))

    def post(self, request):
        name = request.data.get('name')
        app_id = str(uuid.uuid4())
        app = App.objects.create(
            app_id=app_id,
            name=name,
            developer=request.user
        )
        # Generate API key
        ApiKey.objects.create(app=app)
        return Response({'app_id': app_id, 'name': name, 'created_at': app.created_at})

# API Key Management: List and regenerate keys
class ApiKeyListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, app_id):
        try:
            app = App.objects.get(app_id=app_id, developer=request.user)
            keys = ApiKey.objects.filter(app=app).values('key', 'created_at', 'is_active')
            return Response(list(keys))
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)

    def post(self, request, app_id):
        try:
            app = App.objects.get(app_id=app_id, developer=request.user)
            # Deactivate existing keys
            ApiKey.objects.filter(app=app).update(is_active=False)
            # Create new key
            new_key = ApiKey.objects.create(app=app)
            return Response({'key': new_key.key, 'created_at': new_key.created_at})
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)

# OAuth Config Management: Create and list OAuth configurations
class OAuthConfigView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, app_id):
        try:
            app = App.objects.get(app_id=app_id, developer=request.user)
            configs = OAuthConfig.objects.filter(app=app).values(
                'provider', 'client_id', 'redirect_uri', 'created_at'
            )
            return Response(list(configs))
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)

    def post(self, request, app_id):
        try:
            app = App.objects.get(app_id=app_id, developer=request.user)
            provider = request.data.get('provider')
            client_id = request.data.get('client_id')
            client_secret = request.data.get('client_secret')
            redirect_uri = request.data.get('redirect_uri')
            config = OAuthConfig.objects.create(
                app=app,
                provider=provider,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )
            return Response({
                'provider': config.provider,
                'client_id': config.client_id,
                'redirect_uri': config.redirect_uri,
                'created_at': config.created_at
            })
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)



@login_required
def user_list_dashboard(request, app_id):
    try:
        app = App.objects.get(app_id=app_id, developer=request.user)
        users = User.objects.filter(app=app).values(
            'user_id', 'email', 'name', 'auth_method', 'last_login', 'created_at'
        )
        # Add search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            users = users.filter(
                Q(user_id__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(name__icontains=search_query)
            )
        # Pagination
        paginator = Paginator(users, 10)  # 10 users per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return render(request, 'auth_api/user_list.html', {
            'app': app,
            'users': page_obj,
            'search_query': search_query
        })
    except App.DoesNotExist:
        messages.error(request, 'Invalid app')
        return redirect('dashboard')

@login_required
def add_user_dashboard(request, app_id):
    try:
        app = App.objects.get(app_id=app_id, developer=request.user)
        if request.method == 'POST':
            email = request.POST.get('email')
            name = request.POST.get('name', '')
            auth_method = request.POST.get('auth_method', 'manual')
            if not email:
                messages.error(request, 'Email is required')
                return render(request, 'auth_api/add_user.html', {'app': app})
            if auth_method not in ['oauth', 'credentials', 'magic_link', 'manual']:
                messages.error(request, 'Invalid authentication method')
                return render(request, 'auth_api/add_user.html', {'app': app})
            user, created = User.objects.get_or_create(
                app=app,
                email=email,
                defaults={'user_id': str(uuid.uuid4()), 'name': name, 'auth_method': auth_method}
            )
            if created:
                messages.success(request, f'User {email} added successfully')
                return redirect('user_list_dashboard', app_id=app_id)
            else:
                messages.error(request, 'User with this email already exists')
        return render(request, 'auth_api/add_user.html', {'app': app})
    except App.DoesNotExist:
        messages.error(request, 'Invalid app')
        return redirect('dashboard')

# Add User: Allows adding a user to an app via API
class AddUserView(APIView):
    authentication_classes = [ApiKeyAuthentication]
    def post(self, request, app_id):
        try:
            app = App.objects.get(app_id=app_id)
            email = request.data.get('email')
            name = request.data.get('name', '')
            auth_method = request.data.get('auth_method', 'manual')

            if not email:
                return Response({'error': 'Email is required'}, status=400)

            if auth_method not in ['oauth', 'credentials', 'magic_link', 'manual']:
                return Response({'error': 'Invalid authentication method'}, status=400)

            user, created = User.objects.get_or_create(
                app=app,
                email=email,
                defaults={
                    'user_id': str(uuid.uuid4()),
                    'name': name,
                    'auth_method': auth_method
                }
            )

            if created:
                return Response({
                    'user_id': user.user_id,
                    'email': user.email,
                    'name': user.name,
                    'auth_method': user.auth_method,
                    'created_at': user.created_at
                }, status=201)
            else:
                return Response({'error': 'User with this email already exists'}, status=409)
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)

# Check User Login: Checks if a user is logged in
class CheckUserLoginView(APIView):
    authentication_classes = [ApiKeyAuthentication]
    def get(self, request, app_id, user_id):
        try:
            app = App.objects.get(app_id=app_id)
            user = User.objects.get(app=app, user_id=user_id)
            
            # This is a simplified check. A real implementation would
            # involve checking for a valid, non-expired session or token.
            is_logged_in = user.last_login is not None and \
                           (timezone.now() - user.last_login).days < 7

            return Response({
                'user_id': user.user_id,
                'is_logged_in': is_logged_in,
                'last_login': user.last_login
            })
        except (App.DoesNotExist, User.DoesNotExist):
            return Response({'error': 'Invalid app or user'}, status=404)