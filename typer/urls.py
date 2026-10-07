from django import urls
from django.urls import path
from . import views

app_name = 'typer'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('', views.home_view, name='home'),
]