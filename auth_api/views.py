import json
from django.contrib.auth.hashers import make_password, check_password
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
from django.core.mail import send_mail
from rest_framework.authentication import BaseAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
# Custom authentication for API keys
class ApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        # Support both 'Bearer' and 'ApiKey' schemes for flexibility
        if auth_header.startswith('Bearer '):
            key = auth_header.replace('Bearer ', '')
        elif auth_header.startswith('ApiKey '):
            key = auth_header.replace('ApiKey ', '')
        else:
            return None  # Not an authentication type we can handle

        try:
            # Use select_related to optimize the query
            api_key = ApiKey.objects.select_related('app__developer').get(key=key, is_active=True)
            
            # Attach the app object to the request for easy access in views
            request.app = api_key.app
            
            # Return the developer as the user and the key as auth info
            return (api_key.app.developer, api_key)
        except (ApiKey.DoesNotExist, IndexError):
            # Let other authentication methods try if key is invalid
            return None

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
            user, _ = User.objects.update_or_create(
                app=app,
                email=email,
                defaults={
                    'user_id': user_id,
                    'name': name,
                    'auth_method': 'oauth',
                    'password': make_password(None) # Set a non-usable password for OAuth users
                }
            )
            user.last_login = timezone.now()
            user.save()

            # Issue JWT
            refresh = RefreshToken()
            refresh['app_id'] = app.app_id
            refresh['user_id'] = user.user_id
            refresh['email'] = user.email
            return Response({'token': str(refresh.access_token)})
        except (App.DoesNotExist, OAuthConfig.DoesNotExist):
            return Response({'error': 'Invalid app or provider'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

# Credentials Sign-Up: Handles registration and login
class CredentialsSignUpView(APIView):
    authentication_classes = [ApiKeyAuthentication]

    def post(self, request, app_id):
        if not hasattr(request, 'app') or request.app.app_id != app_id:
            raise AuthenticationFailed('Invalid or inactive API key for this app')

        email = request.data.get('email')
        password = request.data.get('password')
        name = request.data.get('name', '')

        if not email or not password:
            return Response({'error': 'Email and password are required'}, status=400)

        try:
            # Check if user already exists
            user = User.objects.get(app=request.app, email=email)
            
            # User exists, check password to log them in
            if check_password(password, user.password):
                user.last_login = timezone.now()
                user.save()
                
                # Issue JWT
                refresh = RefreshToken()
                refresh['app_id'] = request.app.app_id
                refresh['user_id'] = user.user_id
                refresh['email'] = user.email
                return Response({'token': str(refresh.access_token)})
            else:
                return Response({'error': 'Invalid credentials'}, status=401)

        except User.DoesNotExist:
            # User does not exist, create a new one
            user = User.objects.create(
                app=request.app,
                email=email,
                name=name,
                password=make_password(password), # Hash the password
                auth_method='credentials',
                user_id=str(uuid.uuid4())
            )
            user.last_login = timezone.now()
            user.save()

            # Issue JWT
            refresh = RefreshToken()
            refresh['app_id'] = request.app.app_id
            refresh['user_id'] = user.user_id
            refresh['email'] = user.email
            return Response({'token': str(refresh.access_token)}, status=201)

# Credentials Sign-In: Handles email/password login
class CredentialsSignInView(APIView):
    authentication_classes = [ApiKeyAuthentication]
    def post(self, request, app_id):
        if not hasattr(request, 'app') or request.app.app_id != app_id:
            raise AuthenticationFailed('Invalid or inactive API key for this app')

        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email and password are required'}, status=400)

        try:
            user = User.objects.get(app=request.app, email=email)
            if check_password(password, user.password):
                user.last_login = timezone.now()
                user.save()
                
                # Issue JWT
                refresh = RefreshToken()
                refresh['app_id'] = request.app.app_id
                refresh['user_id'] = user.user_id
                refresh['email'] = user.email
                return Response({'token': str(refresh.access_token)})
            else:
                return Response({'error': 'Invalid credentials'}, status=401)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)

# Magic Link: Sends email link, verifies, issues JWT
class MagicLinkView(APIView):
    authentication_classes = [ApiKeyAuthentication]
    def post(self, request, app_id):
        if not hasattr(request, 'app') or request.app.app_id != app_id:
            raise AuthenticationFailed('Invalid or inactive API key for this app')
            
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
                    'password': make_password(None) # Set a non-usable password
                }
            )
            
            refresh = RefreshToken()
            refresh['app_id'] = app.app_id
            refresh['user_id'] = user.user_id
            refresh['email'] = user.email
            
            link = f"{request.scheme}://{request.get_host()}/api/auth/verify/{app_id}?token={str(refresh.access_token)}"
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
            
            # Verify JWT
            from rest_framework_simplejwt.tokens import AccessToken
            token_obj = AccessToken(token)
            user_id = token_obj['user_id']
            
            user = User.objects.get(app=app, user_id=user_id)
            user.last_login = timezone.now()
            user.save()
            
            # Return the same token as it's now verified
            return Response({'token': str(token)})
        except (App.DoesNotExist, User.DoesNotExist):
            return Response({'error': 'Invalid app or user'}, status=404)
        except Exception:
            return Response({'error': 'Invalid token'}, status=401)

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

# User Management: List and create users for an app
class UserListView(APIView):
    authentication_classes = [ApiKeyAuthentication]

    def get(self, request, app_id):
        if not hasattr(request, 'app') or request.app.app_id != app_id:
            raise AuthenticationFailed('Invalid or inactive API key for this app')
            
        try:
            app = App.objects.get(app_id=app_id)
            users = User.objects.filter(app=app).values(
                'user_id', 'email', 'name', 'auth_method', 'last_login', 'created_at'
            )
            return Response(list(users))
        except App.DoesNotExist:
            return Response({'error': 'Invalid app'}, status=404)

    def post(self, request, app_id):
        if not hasattr(request, 'app') or request.app.app_id != app_id:
            raise AuthenticationFailed('Invalid or inactive API key for this app')

        try:
            app = App.objects.get(app_id=app_id)
            email = request.data.get('email')
            name = request.data.get('name', '')
            
            if not email:
                return Response({'error': 'Email is required'}, status=400)

            user, created = User.objects.get_or_create(
                app=app,
                email=email,
                defaults={
                    'user_id': str(uuid.uuid4()),
                    'name': name,
                    'auth_method': 'manual',  # User created via API
                    'password': make_password(None) # Set a non-usable password
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