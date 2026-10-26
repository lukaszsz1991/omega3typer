from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views

app_name = 'typer'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='typer/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('matches/', views.match_list_view, name='match_list'),
    path('predictions/save/', views.predict_bulk_view, name='predict_bulk'),
    path('', views.home_view, name='home'),
    path('ranking/', views.ranking_view, name='ranking'),
    path('groups/', views.group_list_view, name='group_list'),
    path('groups/new/', views.group_create_view, name='group_create'),
    path('groups/<int:group_id>/', views.group_detail_view, name='group_detail'),
    path('groups/join/', views.group_join_view, name='group_join'),
    path("leagues/", views.league_list_view, name="league_list"),
    path("leagues/<int:league_id>/", views.league_detail_view, name="league_detail"),
    path("groups/<int:group_id>/leave/", views.group_leave_view, name="group_leave"),
    path("groups/<int:group_id>/regenerate-code/", views.group_regenerate_code_view, name="group_regenerate_code"),
    path("groups/<int:group_id>/members/<int:user_id>/remove/", views.group_remove_member_view,
         name="group_remove_member"),
    path("matches/<int:match_id>/", views.match_detail_view, name="match_detail"),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='typer/password_reset_form.html',
        email_template_name='typer/password_reset_email.txt',
        subject_template_name='typer/password_reset_subject.txt',
        success_url=reverse_lazy('typer:password_reset_done'),
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='typer/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='typer/password_reset_confirm.html',
        success_url=reverse_lazy('typer:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='typer/password_reset_complete.html',
    ), name='password_reset_complete'),
]
