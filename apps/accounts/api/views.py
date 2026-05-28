from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.accounts.api.serializers import MeSerializer, UsernamePasswordLoginSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UsernamePasswordLoginSerializer,
        responses={
            200: OpenApiResponse(
                description="JWT token pair (access/refresh) + user payload."
            )
        },
    )
    def post(self, request):
        serializer = UsernamePasswordLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


@extend_schema(
    request=None,
    responses={200: MeSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(MeSerializer(request.user).data)

