from django.contrib import admin
from .models import App, User, ApiKey, OAuthConfig

# Register your models here.
admin.site.register(App)
admin.site.register(User)
admin.site.register(ApiKey)
admin.site.register(OAuthConfig)