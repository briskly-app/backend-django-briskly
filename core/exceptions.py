from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None and isinstance(response.data, dict):
        if 'detail' in response.data and len(response.data) == 1:
            response.data = {'error': response.data['detail']}

    return response
