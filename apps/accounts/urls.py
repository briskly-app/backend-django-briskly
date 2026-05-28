from django.urls import path

from apps.accounts.api.views import LoginView, RefreshView, me


urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", me, name="auth-me"),
]

