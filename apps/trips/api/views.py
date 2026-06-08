from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.trips.api.serializers import UserTripConnectionSerializer, UserTripSerializer
from apps.trips.models import UserTrip, UserTripConnection
from apps.trips.services import TripCompletionError, complete_user_trip


@extend_schema(
    request=UserTripSerializer,
    responses={
        200: UserTripSerializer(many=True),
        201: UserTripSerializer,
    },
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def trips_manager(request):
    if request.method == 'GET':
        trips = UserTrip.objects.filter(user=request.user)
        serializer = UserTripSerializer(trips, many=True)
        return Response(serializer.data)

    serializer = UserTripSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@extend_schema(
    request=UserTripSerializer,
    responses={
        200: UserTripSerializer,
        204: OpenApiResponse(description='Deleted.'),
    },
)
@api_view(['GET', 'DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def trip_detail(request, slug):
    trip = get_object_or_404(UserTrip, slug=slug, user=request.user)

    if request.method == 'GET':
        serializer = UserTripSerializer(trip)
        return Response(serializer.data)

    if request.method == 'DELETE':
        trip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = UserTripSerializer(trip, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@extend_schema(
    request=None,
    responses={
        200: UserTripSerializer,
        400: OpenApiResponse(description='Trip completion error.'),
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trip_finalize(request, slug):
    trip = get_object_or_404(UserTrip, slug=slug, user=request.user)

    try:
        complete_user_trip(trip)
    except TripCompletionError as exc:
        return Response({'error': exc.message}, status=exc.status_code)

    serializer = UserTripSerializer(trip)
    return Response(serializer.data)


@extend_schema(
    request=None,
    responses={200: UserTripConnectionSerializer(many=True)},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trip_connections(request, slug):
    trip = get_object_or_404(UserTrip, slug=slug, user=request.user)
    connections = trip.connections.all()
    serializer = UserTripConnectionSerializer(connections, many=True)
    return Response(serializer.data)


@extend_schema(
    request=UserTripConnectionSerializer,
    responses={
        200: UserTripConnectionSerializer,
        204: OpenApiResponse(description='Deleted.'),
    },
)
@api_view(['GET', 'DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def connection_detail(request, id):
    connection = get_object_or_404(
        UserTripConnection.objects.select_related('user_trip'),
        pk=id,
        user_trip__user=request.user,
    )

    if request.method == 'GET':
        serializer = UserTripConnectionSerializer(connection)
        return Response(serializer.data)

    if request.method == 'DELETE':
        connection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = UserTripConnectionSerializer(
        connection,
        data=request.data,
        partial=True,
        context={'request': request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@extend_schema(
    request=UserTripConnectionSerializer,
    responses={201: UserTripConnectionSerializer},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_connection(request):
    serializer = UserTripConnectionSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)
