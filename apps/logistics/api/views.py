from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)

from apps.logistics.api.serializers import (
    CityDetailSerializer,
    CitySerializer,
    DestinationQuerySerializer,
    CityStopsGroupSerializer,
    StopDestinationQuerySerializer,
)
from apps.logistics.models import City, Stop
from apps.logistics.services import (
    find_direct_connections,
    find_direct_connections_from_stop,
    search_stops_grouped_by_city,
)
from apps.logistics.services.attractiveness import city_description_paragraphs

CITIES_TAG = ['cities']
STOPS_TAG = ['stops']
DESTINATIONS_TAG = ['destinations']


@extend_schema(
    tags=DESTINATIONS_TAG,
    request=None,
    parameters=[
        OpenApiParameter(
            name='from_city',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description='City primary key to find connections for.',
        ),
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Departure date (YYYY-MM-DD).',
        ),
        OpenApiParameter(
            name='time',
            type=OpenApiTypes.TIME,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Departure time (HH:MM[:SS]).',
        ),
        OpenApiParameter(
            name='waitingTime',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Max waiting time in minutes for a connection.',
        ),
        OpenApiParameter(
            name='timezone',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Timezone name, e.g. Europe/Warsaw.',
        ),
    ],
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_destinations(request):
    serializer = DestinationQuerySerializer(data=request.GET.dict())

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    v_data = serializer.validated_data
    connections = find_direct_connections(
        city=v_data['from_city'],
        req_date=v_data['date'],
        req_time=v_data['time'],
        waiting_time=v_data['waitingTime'],
        tz_name=v_data['timezone'],
    )

    return Response(connections)


@extend_schema(
    tags=DESTINATIONS_TAG,
    request=None,
    parameters=[
        OpenApiParameter(
            name='from_stop',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Stop primary key (GTFS stop_id) to depart from.',
        ),
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Departure date (YYYY-MM-DD).',
        ),
        OpenApiParameter(
            name='time',
            type=OpenApiTypes.TIME,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Search anchor time — when you are ready to start waiting (HH:MM[:SS]).',
        ),
        OpenApiParameter(
            name='waitingTime',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Max seconds to wait after search time until the bus departs.',
        ),
        OpenApiParameter(
            name='timezone',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Timezone name, e.g. Europe/Warsaw.',
        ),
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Max destination connections returned (default 50, cap 100).',
        ),
        OpenApiParameter(
            name='stops_per_city',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                'Max different destination stops per city (default 3, cap 10). '
                'E.g. Warszawa Centralna and Dworzec Zachodnia as separate results.'
            ),
        ),
    ],
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_destinations_from_stop(request):
    serializer = StopDestinationQuerySerializer(data=request.GET.dict())

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    v_data = serializer.validated_data
    origin_stop = Stop.objects.select_related('place__place_city').get(
        pk=v_data['from_stop'].pk,
    )

    payload = find_direct_connections_from_stop(
        origin_stop=origin_stop,
        req_date=v_data['date'],
        req_time=v_data['time'],
        waiting_time=v_data['waitingTime'],
        tz_name=v_data['timezone'],
        result_limit=v_data.get('limit', 50),
        stops_per_city=v_data.get('stops_per_city', 3),
    )

    return Response(payload)


@extend_schema(
    tags=CITIES_TAG,
    request=None,
    parameters=[
        OpenApiParameter(
            name='q',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Search query (substring match on name/region/country).',
        ),
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Max results. Server caps to 10.',
        ),
    ],
    responses={
        200: inline_serializer(
            name='CitiesResponse',
            fields={
                'results': CitySerializer(many=True),
            },
        ),
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_cities(request):
    search_query = request.GET.get('q', '').strip()

    try:
        limit = int(request.GET.get('limit', 20))
    except ValueError:
        limit = 20

    if limit > 50:
        limit = 50

    if not search_query:
        cities = City.objects.order_by('-city_population')[:limit]
    else:
        cities = City.objects.filter(
            Q(city_name__icontains=search_query)
            | Q(city_region_name__icontains=search_query)
            | Q(city_country_name__icontains=search_query)
            | Q(city_country_code__icontains=search_query),
        ).order_by('-city_population')[:limit]
    serializer = CitySerializer(cities, many=True)

    return Response({'results': serializer.data})


@extend_schema(
    tags=CITIES_TAG,
    request=None,
    responses={200: CityDetailSerializer},
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_city_detail(request, city_id):
    city = get_object_or_404(City, pk=city_id)
    data = CityDetailSerializer(city).data
    data['description_paragraphs'] = city_description_paragraphs(city)
    return Response(data)


@extend_schema(
    tags=STOPS_TAG,
    request=None,
    parameters=[
        OpenApiParameter(
            name='q',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description=(
                'Search query (substring match on stop, city, suburb, region, country).'
            ),
        ),
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Max number of cities in the response (cap 10).',
        ),
        OpenApiParameter(
            name='stops_per_city',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Max stops returned per city (default 5, cap 10).',
        ),
    ],
    responses={
        200: inline_serializer(
            name='StopsResponse',
            fields={
                'results': CityStopsGroupSerializer(many=True),
            },
        ),
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_stops(request):
    search_query = request.GET.get('q', '').strip()

    try:
        city_limit = int(request.GET.get('limit', 10))
    except ValueError:
        city_limit = 10

    try:
        stops_per_city = int(request.GET.get('stops_per_city', 5))
    except ValueError:
        stops_per_city = 5

    if not search_query:
        return Response({'results': []})

    results = search_stops_grouped_by_city(
        search_query,
        city_limit=city_limit,
        stops_per_city=stops_per_city,
    )
    serializer = CityStopsGroupSerializer(results, many=True)
    return Response({'results': serializer.data})
