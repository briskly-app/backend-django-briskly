from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, DatabaseError):
        return Response(
            {
                'error': (
                    'Baza danych jest chwilowo niedostępna. '
                    'Spróbuj ponownie za kilka sekund.'
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    response = exception_handler(exc, context)

    if response is not None and isinstance(response.data, dict):
        if 'detail' in response.data and len(response.data) == 1:
            response.data = {'error': response.data['detail']}

    return response
