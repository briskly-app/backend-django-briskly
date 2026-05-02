from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import DestinationQuerySerializer

from routes.models import City, StopTime
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