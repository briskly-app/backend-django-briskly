from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

NoteHtmlCreateRequest = inline_serializer(
    name='NoteHtmlCreateRequest',
    fields={
        'html_source': serializers.CharField(
            help_text='HTML content for the note.',
        ),
    },
)

NoteImageCreateRequest = inline_serializer(
    name='NoteImageCreateRequest',
    fields={
        'image': serializers.ImageField(
            help_text='Image file (JPEG, PNG or WebP, max 5 MB).',
        ),
    },
)

NoteHtmlUpdateRequest = inline_serializer(
    name='NoteHtmlUpdateRequest',
    fields={
        'html_source': serializers.CharField(),
        'sequence_id': serializers.IntegerField(required=False, min_value=0),
    },
)

NoteImageUpdateRequest = inline_serializer(
    name='NoteImageUpdateRequest',
    fields={
        'image': serializers.ImageField(
            help_text='Replacement image file (JPEG, PNG or WebP, max 5 MB).',
        ),
        'sequence_id': serializers.IntegerField(required=False, min_value=0),
    },
)

NOTE_CREATE_REQUEST = {
    'application/json': NoteHtmlCreateRequest,
    'multipart/form-data': NoteImageCreateRequest,
}

NOTE_UPDATE_REQUEST = {
    'application/json': NoteHtmlUpdateRequest,
    'multipart/form-data': NoteImageUpdateRequest,
}

NOTE_REORDER_REQUEST = {
    'application/json': {
        'type': 'object',
        'additionalProperties': {
            'type': 'integer',
            'minimum': 0,
        },
        'example': {
            '0': 0,
            '1': 1,
        },
        'description': (
            'New order: keys are note ids (from GET /connections/{id}/notes/), '
            'values are sequence_id (0 = first). Include every note you want to reposition.'
        ),
    },
}
