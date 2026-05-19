from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.trips.api.serializers import UserTripConnectionSerializer, UserTripSerializer
from apps.trips.models import UserTrip, UserTripConnection
from apps.trips.services import TripCompletionError, complete_user_trip


@api_view(['GET', 'POST'])
def trips_manager(request):
    if request.method == 'GET':
        trips = UserTrip.objects.all()
        serializer = UserTripSerializer(trips, many=True)
        return Response(serializer.data)

    serializer = UserTripSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET', 'DELETE', 'PATCH'])
def trip_detail(request, slug):
    trip = get_object_or_404(UserTrip, slug=slug)

    if request.method == 'GET':
        serializer = UserTripSerializer(trip)
        return Response(serializer.data)

    if request.method == 'DELETE':
        trip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    try:
        complete_user_trip(trip)
    except TripCompletionError as exc:
        return Response({"error": exc.message}, status=exc.status_code)

    serializer = UserTripSerializer(trip)
    return Response(serializer.data)


@api_view(['GET'])
def get_trip_connections(request, slug):
    trip = get_object_or_404(UserTrip, slug=slug)
    connections = trip.connections.all()
    serializer = UserTripConnectionSerializer(connections, many=True)
    return Response(serializer.data)


@api_view(['GET', 'DELETE'])
def connection_detail(request, pk):
    connection = get_object_or_404(UserTripConnection, pk=pk)

    if request.method == 'GET':
        serializer = UserTripConnectionSerializer(connection)
        return Response(serializer.data)

    connection.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def add_connection(request):
    serializer = UserTripConnectionSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)

    return Response(serializer.errors, status=400)
