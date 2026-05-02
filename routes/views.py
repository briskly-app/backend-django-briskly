from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import DestinationQuerySerializer, CitySerializer, UserTripSerializer, UserTripConnectionSerializer
from django.db.models import Q
from django.shortcuts import get_object_or_404

from routes.models import City, StopTime, UserTrip, UserTripConnection
from routes.services import find_direct_connections

@api_view(['GET'])
def get_destinations(request):
    query_params = request.GET.dict()

    serializer = DestinationQuerySerializer(data=query_params)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    v_data = serializer.validated_data

    connections = find_direct_connections(
        city=v_data['from_city'],
        req_date=v_data['date'],
        req_time=v_data['time'],
        waiting_time=v_data['waitingTime'],
        tz_name=v_data['timezone']
    )

    return Response(connections)

@api_view(['GET'])
def get_cities(request):
    search_query = request.GET.get('q', '').strip()
    limit = request.GET.get('limit', 20)

    if limit > 10:
        limit = 10

    if not search_query:
        return Response({"results": []})

    cities = City.objects.filter(
        Q(city_name__icontains=search_query) |
        Q(city_region_name__icontains=search_query) |
        Q(city_country_name__icontains=search_query) |
        Q(city_country_code__icontains=search_query)
    ).order_by('city_population').reverse();

    cities = cities[:limit]

    serializer = CitySerializer(cities, many=True)
    
    return Response({"results": serializer.data})

@api_view(['GET', 'POST'])
def trips_manager(request):
    if request.method == 'GET':
        trips = UserTrip.objects.all() 
        serializer = UserTripSerializer(trips, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = UserTripSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET'])
def get_trip_detail(request, slug):
    trip = get_object_or_404(UserTrip, slug=slug)
    serializer = UserTripSerializer(trip)
    return Response(serializer.data)

# connections

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
        
    elif request.method == 'DELETE':
        connection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
def add_connection(request):
    serializer = UserTripConnectionSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
        
    return Response(serializer.errors, status=400)