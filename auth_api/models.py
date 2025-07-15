from django.db import models
from django.contrib.auth.models import User
import uuid

# App that developers can create to manage their users and API keys, each app has a unique ID
class App(models.Model):
    app_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    developer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['developer', 'name']  # Ensure unique app names per developer

    def __str__(self):
        return self.name

# User model representing users of the app, 
class User(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='users')
    user_id = models.CharField(max_length=100)
    email = models.EmailField()
    name = models.CharField(max_length=200, blank=True, default='')
    auth_method = models.CharField(max_length=50, choices=[
        ('oauth', 'OAuth'),
        ('credentials', 'Credentials'),
        ('magic_link', 'Email Magic Link'),
    ], default='credentials')
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['app', 'email']  # Unique email per app

    def __str__(self):
        return f"{self.email} ({self.app.name})"

# Unique API key for specific app, used for authenticating  
class ApiKey(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='api_keys')
    key = models.CharField(max_length=200, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"API Key for {self.app.name}"

class OAuthConfig(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='oauth_configs')
    provider = models.CharField(max_length=50, choices=[
        ('github', 'GitHub'),
        ('google', 'Google'),
    ], default='google')
    client_id = models.CharField(max_length=200)
    client_secret = models.CharField(max_length=200)
    redirect_uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['app', 'provider']  # One config per provider per app

    def __str__(self):
        return f"{self.provider} config for {self.app.name}"