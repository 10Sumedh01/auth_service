from django.contrib import admin
from .models import App, User, ApiKey, OAuthConfig

class UserAdmin(admin.ModelAdmin):
    """
    Custom admin view for the User model to enhance usability.
    """
    # Display these fields in the user list
    list_display = ('email', 'name', 'app', 'last_login', 'auth_method', 'created_at')
    
    # Enable filtering by these fields in the right sidebar
    list_filter = ('app', 'auth_method', 'created_at')
    
    # Enable searching by these fields
    search_fields = ('email', 'name', 'user_id', 'app__name')
    
    # Order users by creation date by default
    ordering = ('-created_at',)

# Register your models here.
admin.site.register(App)
admin.site.register(User, UserAdmin)  # Register User with the custom admin class
admin.site.register(ApiKey)
admin.site.register(OAuthConfig)
