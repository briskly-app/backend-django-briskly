from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)

from apps.logistics.api.serializers import CitySerializer, DestinationQuerySerializer
from apps.logistics.models import City
from apps.logistics.services import find_direct_connections


@extend_schema(
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
        )
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

    if limit > 10:
        limit = 10

    if not search_query:
        return Response({"results": []})

    cities = City.objects.filter(
        Q(city_name__icontains=search_query)
        | Q(city_region_name__icontains=search_query)
        | Q(city_country_name__icontains=search_query)
        | Q(city_country_code__icontains=search_query)
    ).order_by('city_population').reverse()

    cities = cities[:limit]
    serializer = CitySerializer(cities, many=True)

    return Response({"results": serializer.data})
