"""Authentication URL patterns."""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/",   views.LoginView.as_view(),   name="login"),
    path("logout/",  views.LogoutView.as_view(),  name="logout"),
    path("register/",views.RegisterView.as_view(),name="register"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("theme/",   views.set_theme,             name="set-theme"),

    # Password reset flow (Django built-in views, custom templates)
    path("password-reset/",
         auth_views.PasswordResetView.as_view(
             template_name="auth/password_reset.html",
             email_template_name="auth/email/password_reset_email.txt",
             subject_template_name="auth/email/password_reset_subject.txt",
             success_url="/auth/password-reset/sent/",
         ),
         name="password_reset"),

    path("password-reset/sent/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="auth/password_reset_done.html",
         ),
         name="password_reset_done"),

    path("password-reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="auth/password_reset_confirm.html",
             success_url="/auth/password-reset/complete/",
         ),
         name="password_reset_confirm"),

    path("password-reset/complete/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="auth/password_reset_complete.html",
         ),
         name="password_reset_complete"),
]
