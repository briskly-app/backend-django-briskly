from django.urls import path

from apps.accounts.api.views import LoginView, RefreshView, me
from apps.accounts.api.oauth_views import GitHubLogin, GoogleLogin


urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", me, name="auth-me"),
    path("auth/google/", GoogleLogin.as_view(), name="auth-google"),
    path("auth/github/", GitHubLogin.as_view(), name="auth-github"),
]

