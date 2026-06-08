import os

from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework import status
from rest_framework.response import Response

from apps.accounts.api.serializers import build_auth_response


class BrisklySocialLoginView(SocialLoginView):
    def post(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=self.build_payload(request))
        self.serializer.is_valid(raise_exception=True)
        self.login()
        return Response(build_auth_response(self.user), status=status.HTTP_200_OK)

    def build_payload(self, request):
        if hasattr(request.data, 'copy'):
            return request.data.copy()
        return dict(request.data)


class GoogleLogin(BrisklySocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = os.environ.get('OAUTH_CALLBACK_URL_GOOGLE', 'postmessage')

    def build_payload(self, request):
        payload = super().build_payload(request)
        if payload.get('id_token') and not payload.get('access_token') and not payload.get('code'):
            payload['access_token'] = payload['id_token']
        return payload


class GitHubLogin(BrisklySocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client
    callback_url = os.environ.get(
        'OAUTH_CALLBACK_URL_GITHUB',
        'http://localhost:5173/auth/callback/github',
    )
