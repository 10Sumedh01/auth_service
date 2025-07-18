from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.views.decorators.http import require_http_methods
from auth_api.models import App, User, ApiKey, OAuthConfig
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
def home(request):
    return render(request, 'auth_service/home.html')

class CustomLoginView(LoginView):
    template_name = 'auth_service/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        # Always redirect to the dashboard after a successful login.
        # The dashboard view will handle showing apps or a prompt to create one.
        return reverse_lazy('dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Login successful!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)

class CustomSignupView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'auth_service/signup.html'

    def form_valid(self, form):
        messages.success(self.request, 'Account created successfully! Please log in.')
        return super().form_valid(form)

@login_required
def dashboard(request):
    apps = App.objects.filter(developer=request.user)
    return render(request, 'auth_service/dashboard.html', {'apps': apps})


@login_required
@require_http_methods(["POST"])
def delete_app(request, app_id):
    """
    Securely delete an app with multiple validation steps
    """
    try:
        # Get app and verify ownership
        app = get_object_or_404(App, app_id=app_id, developer=request.user)
        
        # Security checks
        confirm_app_name = request.POST.get('confirm_app_name')
        password = request.POST.get('password')
        
        # Verify app name matches
        if confirm_app_name != app.name:
            messages.error(request, 'App name confirmation failed. Deletion aborted.')
            return redirect('app_details', app_id=app_id)
        
        # Verify user password
        if not authenticate(username=request.user.username, password=password):
            messages.error(request, 'Password verification failed. Deletion aborted.')
            return redirect('app_details', app_id=app_id)
        
        # Get statistics before deletion (for logging)
        user_count = User.objects.filter(app=app).count()
        api_key_count = ApiKey.objects.filter(app=app).count()
        
        # Perform deletion in a transaction
        with transaction.atomic():
            # Delete all related data
            User.objects.filter(app=app).delete()
            ApiKey.objects.filter(app=app).delete()
            OAuthConfig.objects.filter(app=app).delete()
            
            # Delete the app itself
            app_name = app.name
            app.delete()
        
        # Log the deletion (optional - add logging here)
        messages.success(
            request, 
            f'App "{app_name}" has been permanently deleted along with {user_count} users and {api_key_count} API keys.'
        )
        
        return redirect('dashboard')
        
    except Exception as e:
        messages.error(request, f'An error occurred while deleting the app: {str(e)}')
        return redirect('app_details', app_id=app_id)



@login_required
def create_app_dashboard(request):
    if request.method == 'POST':
        name = request.POST.get('app_name')
        if not name:
            messages.error(request, 'App name is required')
            return render(request, 'auth_service/create_app.html')
        try:
            app = App.objects.create(
                name=name,
                developer=request.user
            )
            api_key = ApiKey.objects.create(app=app)
            messages.success(request, f'App {name} created successfully!')
            return render(request, 'auth_service/create_app.html', {
                'app_id': app.app_id,
                'api_key': api_key.key
            })
        except Exception as e:
            messages.error(request, f'Error creating app: {e}')
    return render(request, 'auth_service/create_app.html')

@login_required
def app_details(request, app_id):
    # app = get_object_or_404(App, app_id=app_id, developer=request.user)
    # api_key = ApiKey.objects.filter(app=app).first()
    # return render(request, 'auth_service/app_details.html', {'app': app, 'api_key': api_key})
    try:
        app = get_object_or_404(App, app_id=app_id, developer=request.user)
        api_key = ApiKey.objects.filter(app=app, is_active=True).first()
        
        # Get statistics
        user_count = User.objects.filter(app=app).count()
        api_key_count = ApiKey.objects.filter(app=app).count()
        days_since_created = (timezone.now() - app.created_at).days
        
        context = {
            'app': app,
            'api_key': api_key,
            'user_count': user_count,
            'api_key_count': api_key_count,
            'days_since_created': days_since_created,
        }
        
        return render(request, 'auth_service/app_details.html', context)
        
    except App.DoesNotExist:
        messages.error(request, 'App not found or access denied.')
        return redirect('dashboard')

@login_required
def user_list_dashboard(request, app_id):
    try:
        # app = App.objects.get(app_id=app_id, developer=request.user)
        app = App.objects.select_related('developer').get(app_id=app_id, developer=request.user)
        # users = User.objects.filter(app=app).values(
        #     'user_id', 'email', 'name', 'auth_method', 'last_login', 'created_at'
        # )
        users = User.objects.filter(app=app).values(
            'user_id', 'email', 'name', 'auth_method', 'last_login', 'created_at'
        ).order_by('-created_at')  # Add ordering
        # Implementing search functionality
        search_query = request.GET.get('search', '').strip()
        if search_query:
            users = users.filter(
                Q(user_id__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(name__icontains=search_query)
            )
        # Pagination
        paginator = Paginator(users, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return render(request, 'auth_service/user_list.html', {
            'app': app,
            'users': page_obj,
            'page_obj': page_obj,  # Add this for pagination controls
            'search_query': search_query,
            'total_users': paginator.count,  # Add total count
        })
    except App.DoesNotExist:
        messages.error(request, 'Invalid app or access denied.')
        return redirect('login')

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
                return render(request, 'auth_service/add_user.html', {'app': app})
            if auth_method not in ['oauth', 'credentials', 'magic_link', 'manual']:
                messages.error(request, 'Invalid authentication method')
                return render(request, 'auth_service/add_user.html', {'app': app})
            user, created = User.objects.get_or_create(
                app=app,
                user_id=str(uuid.uuid4()),
                defaults={'email': email, 'name': name, 'auth_method': auth_method}
            )
            if created:
                messages.success(request, f'User {email} added successfully')
                return redirect('user_list_dashboard', app_id=app_id)
            else:
                messages.error(request, 'User with this email already exists')
        return render(request, 'auth_service/add_user.html', {'app': app})
    except App.DoesNotExist:
        messages.error(request, 'Invalid app')
        return redirect('login')