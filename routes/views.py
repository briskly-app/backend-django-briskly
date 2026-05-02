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

@api_view(['GET', 'DELETE', 'PATCH'])
def trip_detail(request, slug):
    trip = get_object_or_404(UserTrip, slug=slug)

    if request.method == 'GET':
        serializer = UserTripSerializer(trip)
        return Response(serializer.data)
    elif request.method == 'DELETE':
        trip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    elif request.method == 'PATCH':
        connections = trip.connections.all()

        if not connections.exists():
            return Response({"error": "Cannot complete an empty trip."}, status=400)

        trip.start_date = connections.first().departure_date
        trip.end_date = connections.last().arrival_date
        
        visited_cities = [];

        for connection in connections:
            start_city = connection.starting_stop.place.place_city
            end_city = connection.destination_stop.place.place_city

            if not start_city in visited_cities:
                visited_cities.append(start_city)
            if not end_city in visited_cities:
                visited_cities.append(end_city)

        unique_countries = set()
        unique_regions = set()
        
        current_population = 0

        for city in visited_cities:

            if city.city_thumbnail_url and current_population < city.city_population:
                trip.thumbnail_url = city.city_thumbnail_url
                current_population = city.city_population

            if city.city_country_name not in unique_countries:
                unique_countries.add(city.city_country_name)
            if city.city_region_name not in unique_regions:
                unique_regions.add(city.city_region_name)

        name_elements = []

        if len(visited_cities) <= 2:
            name_elements = [c.city_name for c in visited_cities]
        elif len(unique_countries) > 1:
            name_elements = unique_countries
        elif len(unique_regions) > 1:
            name_elements = unique_regions
        else:
            name_elements = [c.city_name for c in visited_cities]

        if len(name_elements) > 3:
            middle_index = len(name_elements) // 2
            final_name_parts = [
                name_elements[0], 
                name_elements[middle_index], 
                name_elements[-1]
            ]
        else:
            final_name_parts = name_elements

        if len(final_name_parts) == 3:
            trip.name = f"{final_name_parts[0]}, {final_name_parts[1]} and {final_name_parts[2]}"
        elif len(final_name_parts) == 2:
            trip.name = f"{final_name_parts[0]} and {final_name_parts[1]}"
        else:
            trip.name = final_name_parts[0]
        
        trip.save()
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