from django.db import models
from django.contrib.auth.models import User
import uuid


# App that developers can create to manage their users and API keys, each app has a unique ID
class App(models.Model):
    """
    Represents an application created by a developer.

    Each app has a unique ID and serves as a container for its own set of
    users, API keys, and authentication configurations.
    """
    app_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    developer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["developer", "name"]  # Ensure unique app names per developer

    def __str__(self):
        return self.name


# User model representing users of the app,
class User(models.Model):
    """
    Represents an end-user of a specific App.

    Each user is scoped to a single application and can have various
    authentication methods. Their email address must be unique within the app.
    """
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="users")
    user_id = models.CharField(max_length=100)
    email = models.EmailField()
    name = models.CharField(max_length=200, blank=True, default="")
    password = models.CharField(max_length=128)  # Field to store hashed password
    auth_method = models.CharField(
        max_length=50,
        choices=[
            ("oauth", "OAuth"),
            ("credentials", "Credentials"),
            ("magic_link", "Email Magic Link"),
            ("manual", "Manual Entry"),
        ],
        default="credentials",
    )
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["app", "email"]  # Unique email per app

    def __str__(self):
        return f"{self.email} ({self.app.name})"


# Unique API key for specific app, used for authenticating
class ApiKey(models.Model):
    """
    Represents a unique API key for a specific App.

    API keys are used to authenticate requests made to the service on behalf
    of an application.
    """
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="api_keys")
    key = models.CharField(max_length=200, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"API Key for {self.app.name}"


# Authentication configuration for OAuth providers like GitHub or Google
class OAuthConfig(models.Model):
    """
    Stores OAuth 2.0 configuration for an App and a specific provider.

    This model holds the client ID, client secret, and redirect URI required
    to perform OAuth flows with providers like GitHub or Google.
    """
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="oauth_configs")
    provider = models.CharField(
        max_length=50,
        choices=[
            ("github", "GitHub"),
            ("google", "Google"),
        ],
        default="google",
    )
    client_id = models.CharField(max_length=200)
    client_secret = models.CharField(max_length=200)
    redirect_uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["app", "provider"]  # One config per provider per app

    def __str__(self):
        return f"{self.provider} config for {self.app.name}"
