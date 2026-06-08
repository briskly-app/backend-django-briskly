from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.accounts.api.serializers import (
    EmailPasswordLoginSerializer,
    MeSerializer,
    MeUpdateSerializer,
    RegisterSerializer,
    build_auth_response,
)
from apps.trips.services.stats import build_user_dashboard_stats


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=EmailPasswordLoginSerializer,
        responses={
            200: OpenApiResponse(
                description='JWT token pair (access/refresh) + user payload.',
            ),
        },
    )
    def post(self, request):
        serializer = EmailPasswordLoginSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                description='JWT token pair (access/refresh) + user payload.',
            ),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(build_auth_response(user), status=status.HTTP_201_CREATED)


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


@extend_schema(
    request=MeUpdateSerializer,
    responses={200: MeSerializer},
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == 'GET':
        return Response(MeSerializer(request.user).data)

    serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(MeSerializer(request.user).data)


@extend_schema(
    request=None,
    responses={200: OpenApiResponse(description='Dashboard stats for the current user.')},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_stats(request):
    return Response(build_user_dashboard_stats(request.user))
