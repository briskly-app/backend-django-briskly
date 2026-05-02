from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import DestinationQuerySerializer, CitySerializer, UserTripSerializer, UserTripConnectionSerializer
from django.db.models import Q

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

@api_view(['POST'])
def create_trip(request):
    new_trip = UserTrip.objects.create()
    serializer = UserTripSerializer(new_trip)
    return Response(serializer.data, status=201)

@api_view(['POST'])
def add_connection(request):
    serializer = UserTripConnectionSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
        
    return Response(serializer.errors, status=400)