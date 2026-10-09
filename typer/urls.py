from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'typer'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='typer/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('matches/', views.match_list_view, name='match_list'),
    path('', views.home_view, name='home'),
]