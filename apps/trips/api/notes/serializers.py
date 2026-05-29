from rest_framework import serializers

from apps.trips.models import UserTripConnectionNote


class UserTripConnectionNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTripConnectionNote
        fields = [
            'id',
            'sequence_id',
            'user_trip_connection',
            'html_source',
            'image_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'sequence_id',
            'user_trip_connection',
            'created_at',
            'updated_at',
        ]


class UserTripConnectionNoteCreateSerializer(serializers.Serializer):
    html_source = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)

    def validate(self, attrs):
        html_source = attrs.get('html_source', '').strip()
        image = attrs.get('image')
        has_html = bool(html_source)
        has_image = image is not None

        if has_html == has_image:
            raise serializers.ValidationError(
                'Provide exactly one of html_source or image.',
            )

        attrs['html_source'] = html_source
        return attrs


class UserTripConnectionNoteUpdateSerializer(serializers.Serializer):
    html_source = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)
    sequence_id = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('At least one field is required.')

        html_provided = 'html_source' in attrs
        image_provided = 'image' in attrs

        if html_provided and image_provided:
            raise serializers.ValidationError(
                'Provide either html_source or image, not both.',
            )

        if html_provided:
            attrs['html_source'] = attrs['html_source'].strip()
            if not attrs['html_source']:
                raise serializers.ValidationError(
                    {'html_source': 'This field may not be blank.'},
                )

        return attrs


class NoteReorderSerializer(serializers.Serializer):
    """Map of note id (string key in JSON) to new sequence_id."""

    def run_validation(self, data=serializers.empty):
        if data is serializers.empty:
            raise serializers.ValidationError({
                'non_field_errors': [
                    'Request body is required. Example: {"4": 0, "5": 1} '
                    '(note id → new sequence_id, 0 = first).',
                ],
            })
        return super().run_validation(data)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({
                'non_field_errors': [
                    'Expected a JSON object mapping note id to sequence_id.',
                ],
            })

        result = {}
        errors = {}

        for key, value in data.items():
            try:
                note_id = int(key)
            except (TypeError, ValueError):
                errors[str(key)] = 'Note id must be an integer.'
                continue

            try:
                sequence_id = int(value)
            except (TypeError, ValueError):
                errors[str(key)] = 'sequence_id must be an integer.'
                continue

            if sequence_id < 0:
                errors[str(key)] = 'sequence_id must be zero or greater.'
                continue

            result[note_id] = sequence_id

        if errors:
            raise serializers.ValidationError(errors)

        if not result:
            raise serializers.ValidationError({
                'non_field_errors': [
                    'Reorder map must not be empty. Example: {"4": 0, "5": 1}',
                ],
            })

        return result
