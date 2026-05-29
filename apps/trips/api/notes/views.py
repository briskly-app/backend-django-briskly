from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.trips.api.notes.openapi import (
    NOTE_CREATE_REQUEST,
    NOTE_REORDER_REQUEST,
    NOTE_UPDATE_REQUEST,
)
from apps.trips.api.notes.serializers import (
    NoteReorderSerializer,
    UserTripConnectionNoteCreateSerializer,
    UserTripConnectionNoteSerializer,
    UserTripConnectionNoteUpdateSerializer,
)
from apps.trips.models import UserTripConnection, UserTripConnectionNote
from apps.trips.services.note_ordering import next_sequence_id, reorder_connection_notes
from apps.trips.services.note_storage import NoteImageUploadError, delete_note_image, upload_note_image

NOTES_TAG = ['notes']


def _get_user_connection(request, connection_id: int) -> UserTripConnection:
    return get_object_or_404(
        UserTripConnection.objects.select_related('user_trip'),
        pk=connection_id,
        user_trip__user=request.user,
    )


def _get_user_note(
    request,
    note_id: int,
    *,
    connection_id: int | None = None,
) -> UserTripConnectionNote:
    queryset = UserTripConnectionNote.objects.select_related(
        'user_trip_connection__user_trip',
    ).filter(
        pk=note_id,
        user_trip_connection__user_trip__user=request.user,
    )
    if connection_id is not None:
        queryset = queryset.filter(user_trip_connection_id=connection_id)

    note = queryset.first()
    if note is None:
        raise NotFound(
            'Note not found. Use the note id from POST/GET list response '
            f'(field "id"), not the connection id. '
            f'Nested URL: /api/connections/{connection_id or "<connection_id>"}/notes/<note_id>/',
        )
    return note


def _handle_note_detail(request, note: UserTripConnectionNote):
    if request.method == 'GET':
        return Response(UserTripConnectionNoteSerializer(note).data)

    if request.method == 'DELETE':
        if note.is_image_note:
            delete_note_image(note.image_url)
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    update_serializer = UserTripConnectionNoteUpdateSerializer(data=request.data, partial=True)
    update_serializer.is_valid(raise_exception=True)
    validated = update_serializer.validated_data

    if 'sequence_id' in validated and validated['sequence_id'] != note.sequence_id:
        conflict = note.user_trip_connection.notes.filter(
            sequence_id=validated['sequence_id'],
        ).exclude(pk=note.pk).exists()
        if conflict:
            raise ValidationError(
                {'sequence_id': 'Another note on this connection already uses this sequence_id.'},
            )
        note.sequence_id = validated['sequence_id']

    if 'html_source' in validated:
        if note.is_image_note:
            raise ValidationError({'html_source': 'Cannot set html_source on an image note.'})
        note.html_source = validated['html_source']

    if 'image' in validated:
        if not note.is_image_note:
            raise ValidationError({'image': 'Cannot replace image on an HTML note.'})
        try:
            new_url = upload_note_image(
                request.user.pk,
                note.user_trip_connection_id,
                validated['image'],
            )
        except NoteImageUploadError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        delete_note_image(note.image_url)
        note.image_url = new_url

    note.save()
    return Response(UserTripConnectionNoteSerializer(note).data)


@extend_schema(
    methods=['GET'],
    tags=NOTES_TAG,
    request=None,
    responses={200: UserTripConnectionNoteSerializer(many=True)},
)
@extend_schema(
    methods=['POST'],
    tags=NOTES_TAG,
    request=NOTE_CREATE_REQUEST,
    responses={
        201: UserTripConnectionNoteSerializer,
        400: OpenApiResponse(description='Validation or upload error.'),
    },
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def connection_notes(request, connection_id):
    connection = _get_user_connection(request, connection_id)

    if request.method == 'GET':
        notes = connection.notes.all()
        serializer = UserTripConnectionNoteSerializer(notes, many=True)
        return Response(serializer.data)

    create_serializer = UserTripConnectionNoteCreateSerializer(data=request.data)
    create_serializer.is_valid(raise_exception=True)
    validated = create_serializer.validated_data

    note_kwargs = {
        'user_trip_connection': connection,
        'sequence_id': next_sequence_id(connection),
        'html_source': '',
        'image_url': '',
    }

    if validated.get('html_source'):
        note_kwargs['html_source'] = validated['html_source']
    else:
        try:
            note_kwargs['image_url'] = upload_note_image(
                request.user.pk,
                connection.pk,
                validated['image'],
            )
        except NoteImageUploadError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {'error': f'Image upload failed: {exc}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    note = UserTripConnectionNote.objects.create(**note_kwargs)
    return Response(
        UserTripConnectionNoteSerializer(note).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=NOTES_TAG,
    request=NOTE_REORDER_REQUEST,
    responses={
        200: UserTripConnectionNoteSerializer(many=True),
        400: OpenApiResponse(description='Invalid reorder payload.'),
    },
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def connection_notes_reorder(request, connection_id):
    connection = _get_user_connection(request, connection_id)

    reorder_serializer = NoteReorderSerializer(data=request.data)
    reorder_serializer.is_valid(raise_exception=True)
    sequence_map = reorder_serializer.validated_data

    try:
        reorder_connection_notes(connection, sequence_map)
    except ValueError as exc:
        raise ValidationError({'error': str(exc)}) from exc
    except Exception as exc:
        return Response(
            {'error': f'Failed to reorder notes: {exc}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    notes = connection.notes.all()
    return Response(UserTripConnectionNoteSerializer(notes, many=True).data)


@extend_schema(
    methods=['GET'],
    tags=NOTES_TAG,
    request=None,
    responses={200: UserTripConnectionNoteSerializer},
)
@extend_schema(
    methods=['PATCH'],
    tags=NOTES_TAG,
    request=NOTE_UPDATE_REQUEST,
    responses={
        200: UserTripConnectionNoteSerializer,
        400: OpenApiResponse(description='Validation or upload error.'),
    },
)
@extend_schema(
    methods=['DELETE'],
    tags=NOTES_TAG,
    request=None,
    responses={204: OpenApiResponse(description='Deleted.')},
)
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def connection_note_detail(request, connection_id, note_id):
    _get_user_connection(request, connection_id)
    note = _get_user_note(request, note_id, connection_id=connection_id)
    return _handle_note_detail(request, note)


@extend_schema(
    methods=['GET'],
    tags=NOTES_TAG,
    request=None,
    responses={200: UserTripConnectionNoteSerializer},
)
@extend_schema(
    methods=['PATCH'],
    tags=NOTES_TAG,
    request=NOTE_UPDATE_REQUEST,
    responses={
        200: UserTripConnectionNoteSerializer,
        400: OpenApiResponse(description='Validation or upload error.'),
    },
)
@extend_schema(
    methods=['DELETE'],
    tags=NOTES_TAG,
    request=None,
    responses={204: OpenApiResponse(description='Deleted.')},
)
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def note_detail(request, id):
    note = _get_user_note(request, id)
    return _handle_note_detail(request, note)


connection_notes.parser_classes = [JSONParser, MultiPartParser, FormParser]
connection_note_detail.parser_classes = [JSONParser, MultiPartParser, FormParser]
note_detail.parser_classes = [JSONParser, MultiPartParser, FormParser]
