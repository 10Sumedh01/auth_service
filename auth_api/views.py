# import json
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken

# from allauth.socialaccount.models import SocialToken #checkout allauth docs 
# for future reference
from .models import App, User, ApiKey, OAuthConfig
import uuid
import requests
from django.utils import timezone
from django.shortcuts import redirect

# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.core.paginator import Paginator
# from django.db.models import Q
from django.core.mail import send_mail
from rest_framework.authentication import BaseAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed

# from rest_framework.permissions import IsAuthenticated
from urllib.parse import urlencode

# from django.core.paginator import Paginator
# from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache
# import argon2
# import os


def generate_jwt_token(user, app):
    """Generate JWT token for user with app context"""
    cache_key = f"jwt_token:{user.user_id}:{app.app_id}"
    token = cache.get(cache_key)
    if not token:
        refresh = RefreshToken.for_user(user)
        refresh["app_id"] = app.app_id
        refresh["user_id"] = user.user_id
        refresh["email"] = user.email
        token = str(refresh.access_token)
        cache.set(cache_key, token, timeout=3600)  # Cache for 1 hour
    return token


# Custom authentication for API keys
class ApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        # Support both 'Bearer' and 'ApiKey' schemes for flexibility
        if auth_header.startswith("Bearer "):
            key = auth_header.replace("Bearer ", "")
        elif auth_header.startswith("ApiKey "):
            key = auth_header.replace("ApiKey ", "")
        else:
            return None  # Not an authentication type we can handle

        try:
            # Use select_related to optimize the query
            api_key = ApiKey.objects.select_related("app__developer").get(
                key=key, is_active=True
            )

            # Attach the app object to the request for easy access in views
            request.app = api_key.app

            # Return the developer as the user and the key as auth info
            return (api_key.app.developer, api_key)
        except (ApiKey.DoesNotExist, IndexError):
            # Let other authentication methods try if key is invalid
            return None


# OAuth Redirect: Initiates OAuth flow (e.g., GitHub)
class OAuthRedirectView(APIView):
    def get(self, request, provider, app_id):
        try:
            cache_key = f"oauth_config:{app_id}:{provider}"
            oauth_config = cache.get(cache_key)
            if not oauth_config:
                oauth_config = OAuthConfig.objects.select_related("app").get(
                    app__app_id=app_id, provider=provider
                )
                cache.set(cache_key, oauth_config, timeout=300)  # Cache for 5 minutes
            app = oauth_config.app

            # Build redirect URI with app_id included
            redirect_uri = (
                f"http://localhost:8000/api/auth/callback/{provider}/{app_id}"
            )

            redirect_url = (
                f"https://{provider}.com/login/oauth/authorize"
                f"?client_id={oauth_config.client_id}"
                f"&redirect_uri={redirect_uri}"
                f"&scope=user:email"
            )
            return Response({"redirect_url": redirect_url})
        except (App.DoesNotExist, OAuthConfig.DoesNotExist):
            return Response({"error": "Invalid app or provider"}, status=404)


# OAuth Callback: Handles OAuth callback, stores user, issues JWT, then redirects
class OAuthCallbackView(APIView):
    def get(self, request, provider, app_id):
        try:
            cache_key = f"oauth_config:{app_id}:{provider}"
            oauth_config = cache.get(cache_key)
            if not oauth_config:
                oauth_config = OAuthConfig.objects.select_related("app").get(
                    app__app_id=app_id, provider=provider
                )
                cache.set(cache_key, oauth_config, timeout=300)  # Cache for 5 minutes
            app = oauth_config.app
            app = cache.get(f"app:{app_id}")
            if not app:
                app = App.objects.get(app_id=app_id)
                cache.set(f"app:{app_id}", app, timeout=300)
            code = request.query_params.get("code")
            if not code:
                return Response(
                    {"error": "Authorization code not provided"}, status=400
                )

            # Exchange code for access token
            token_url = f"https://{provider}.com/login/oauth/access_token"
            response = requests.post(
                token_url,
                data={
                    "client_id": oauth_config.client_id,
                    "client_secret": oauth_config.client_secret,
                    "code": code,
                    "redirect_uri": f"http://localhost:8000/api/auth/callback/{provider}/{app_id}",
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )

            if response.status_code != 200:
                return Response({"error": "Token exchange failed"}, status=400)

            token_data = response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                return Response({"error": "Access token not found"}, status=400)

            # Fetch user data (example: GitHub)
            user_response = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if user_response.status_code != 200:
                return Response({"error": "Failed to fetch user data"}, status=400)

            user_data = user_response.json()
            user_id = str(user_data.get("id"))
            email = user_data.get("email") or f"{user_id}@{provider}.com"
            name = user_data.get("name") or ""

            # Store or update user
            user, _ = User.objects.update_or_create(
                app=app,
                email=email,
                defaults={
                    "user_id": user_id,
                    "name": name,
                    "auth_method": "oauth",
                    "password": make_password(None),  # unusable password
                    "last_login": timezone.now(),
                },
            )
            # user.last_login = timezone.now()
            # user.save()

            # Issue JWT
            refresh = RefreshToken.for_user(user)
            refresh["app_id"] = app.app_id
            refresh["user_id"] = user.user_id
            refresh["email"] = user.email
            access_token_jwt = str(refresh.access_token)

            redirect_uri = oauth_config.redirect_uri  # Provided by dev
            query_string = urlencode({"token": access_token_jwt})
            return redirect(f"{redirect_uri}?{query_string}")

        except (App.DoesNotExist, OAuthConfig.DoesNotExist):
            return Response({"error": "Invalid app or provider"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CredentialsSignUpView(APIView):
    authentication_classes = [ApiKeyAuthentication]

    def post(self, request, app_id):
        cache_key = f"app:{app_id}"
        app = cache.get(cache_key)
        if not app:
            try:
                app = App.objects.get(app_id=app_id)
                cache.set(cache_key, app, timeout=300)  # Cache for 5 minutes
            except App.DoesNotExist:
                raise AuthenticationFailed("Invalid app")
        request.app = app

        email = request.data.get("email")
        password = request.data.get("password")
        name = request.data.get("name", "")

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=400)

        try:
            # Check if user already exists
            user = User.objects.get(app=request.app, email=email)

            # User exists, check password to log them in
            if check_password(password, user.password):
                user.last_login = timezone.now()
                user.save(update_fields=["last_login"])

                # Issue JWT
                # refresh = RefreshToken()
                # refresh['app_id'] = request.app.app_id
                # refresh['user_id'] = user.user_id
                # refresh['email'] = user.email
                token = generate_jwt_token(user, request.app)
                return Response({"token": token})
            else:
                return Response({"error": "Invalid credentials"}, status=401)

        except User.DoesNotExist:
            # User does not exist, create a new one
            user = User.objects.create(
                app=request.app,
                email=email,
                name=name,
                password=make_password(password),
                auth_method="credentials",
                user_id=str(uuid.uuid4()),
                last_login=timezone.now(),
            )
            user.save()

            # Issue JWT
            # refresh = RefreshToken()
            # refresh['app_id'] = request.app.app_id
            # refresh['user_id'] = user.user_id
            # refresh['email'] = user.email
            token = generate_jwt_token(user, request.app)
            return Response({"token": token}, status=201)


# Credentials Sign-In: Handles email/password login
class CredentialsSignInView(APIView):
    authentication_classes = [ApiKeyAuthentication]

    def post(self, request, app_id):
        cache_key = f"app:{app_id}"
        app = cache.get(cache_key)
        if not app:
            try:
                app = App.objects.get(app_id=app_id)
                cache.set(cache_key, app, timeout=300)  # Cache for 5 minutes
            except App.DoesNotExist:
                raise AuthenticationFailed("Invalid app")
        request.app = app

        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=400)

        try:
            user = User.objects.get(app=request.app, email=email)
            if check_password(password, user.password):
                user.last_login = timezone.now()
                user.save()

                # Issue JWT
                token = generate_jwt_token(user, request.app)
                return Response({"token": token})
            else:
                return Response({"error": "Invalid credentials"}, status=401)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=401)


# Magic Link: Sends email link, verifies, issues JWT
class MagicLinkView(APIView):
    authentication_classes = [ApiKeyAuthentication]

    def post(self, request, app_id):
        cache_key = f"app:{app_id}"
        app = cache.get(cache_key)
        if not app:
            try:
                app = App.objects.get(app_id=app_id)
                cache.set(cache_key, app, timeout=300)  # Cache for 5 minutes
            except App.DoesNotExist:
                return Response({"error": "Invalid app"}, status=404)
        request.app = app

        email = request.data.get("email")
        if not email or "@" not in email:
            return Response({"error": "A valid email is required"}, status=400)

        user, _ = User.objects.get_or_create(
            app=request.app,
            email=email,
            defaults={
                "user_id": str(uuid.uuid4()),
                "name": "",
                "auth_method": "magic_link",
                "password": make_password(None),  # Set a non-usable password
            },
        )

        refresh = RefreshToken()

        refresh = RefreshToken()
        refresh["app_id"] = app.app_id
        refresh["user_id"] = user.user_id
        refresh["email"] = user.email

        link = f"{request.scheme}://{request.get_host()}/api/auth/verify/{app_id}?token={str(refresh.access_token)}"
        send_mail(
            "Sign In to Your App",
            f"Click to sign in: {link}",
            "from@your-auth-service.com",
            [email],
            fail_silently=False,
        )
        return Response({"success": True})


# Magic Link Verification: Verifies token, updates last_login, returns JWT
class MagicLinkVerifyView(APIView):
    def get(self, request, app_id):
        try:
            token = request.query_params.get("token")

            app = cache.get(f"app:{app_id}")
            if not app:
                app = App.objects.get(app_id=app_id)
                cache.set(f"app:{app_id}", app, timeout=300)

            # Verify JWT
            from rest_framework_simplejwt.tokens import AccessToken

            token_obj = AccessToken(token)
            user_id = token_obj["user_id"]

            user = User.objects.get(app=app, user_id=user_id)
            user.last_login = timezone.now()
            user.save()

            # Return the same token as it's now verified
            return Response({"token": str(token)})
        except (App.DoesNotExist, User.DoesNotExist):
            return Response({"error": "Invalid app or user"}, status=404)
        except Exception:
            return Response({"error": "Invalid token"}, status=401)


# Check User Login: Checks if a user is logged in
class CheckUserLoginView(APIView):
    authentication_classes = [ApiKeyAuthentication]

    def get(self, request, app_id, user_id):
        try:
            app = cache.get(f"app:{app_id}")
            if not app:
                app = App.objects.get(app_id=app_id)
                cache.set(f"app:{app_id}", app, timeout=300)

            user = User.objects.get(app=app, user_id=user_id)

            # This is a simplified check. A real implementation would
            # involve checking for a valid, non-expired session or token.
            is_logged_in = (
                user.last_login is not None
                and (timezone.now() - user.last_login).days < 7
            )

            return Response(
                {
                    "user_id": user.user_id,
                    "is_logged_in": is_logged_in,
                    "last_login": user.last_login,
                }
            )
        except (App.DoesNotExist, User.DoesNotExist):
            return Response({"error": "Invalid app or user"}, status=404)
