from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from auth_api.models import App, User, ApiKey
import uuid

class CustomLoginView(LoginView):
    template_name = 'auth_service/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        app = App.objects.filter(developer=self.request.user).first()
        if app:
            return reverse_lazy('dashboard')
        return reverse_lazy('login') # Redirect to login if no app, or a generic dashboard

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
def create_app_dashboard(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if not name:
            messages.error(request, 'App name is required')
            return render(request, 'auth_service/create_app.html')
        try:
            app_id = str(uuid.uuid4())
            app = App.objects.create(
                app_id=app_id,
                name=name,
                developer=request.user
            )
            ApiKey.objects.create(app=app)
            messages.success(request, f'App {name} created successfully!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Error creating app: {e}')
    return render(request, 'auth_service/create_app.html')

@login_required
def user_list_dashboard(request, app_id):
    try:
        app = App.objects.get(app_id=app_id, developer=request.user)
        users = User.objects.filter(app=app).values(
            'user_id', 'email', 'name', 'auth_method', 'last_login', 'created_at'
        )
        search_query = request.GET.get('search', '')
        if search_query:
            users = users.filter(
                Q(user_id__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(name__icontains=search_query)
            )
        paginator = Paginator(users, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return render(request, 'auth_service/user_list.html', {
            'app': app,
            'users': page_obj,
            'search_query': search_query
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