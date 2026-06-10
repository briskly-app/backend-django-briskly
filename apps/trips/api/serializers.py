from rest_framework import serializers

from apps.logistics.services.attractiveness import city_description_paragraphs
from apps.trips.models import UserTrip, UserTripConnection


def _serialize_connection_stop(stop):
    if not stop:
        return None

    city = stop.place.place_city if stop.place else None
    payload = {
        'stop_id': stop.stop_id,
        'stop_name': stop.stop_name,
        'longitude': stop.stop_lon,
        'latitude': stop.stop_lat,
    }

    if city:
        payload.update(
            {
                'city_id': city.city_id,
                'city_name': city.city_name,
                'region': city.city_region_name,
                'country_name': city.city_country_name,
                'country_code': city.city_country_code,
                'thumbnail_url': city.city_thumbnail_url,
                'city_population': city.city_population,
                'city_description': city.city_description,
                'description_paragraphs': city_description_paragraphs(city),
            },
        )

    return payload


class UserTripSerializer(serializers.ModelSerializer):
    journal_entry_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = UserTrip
        fields = [
            'slug',
            'name',
            'description',
            'start_date',
            'end_date',
            'thumbnail_url',
            'created_at',
            'journal_entry_count',
        ]
        read_only_fields = ['id', 'slug', 'created_at']


class UserTripConnectionSerializer(serializers.ModelSerializer):
    user_trip = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=UserTrip.objects.none(),
    )

    class Meta:
        model = UserTripConnection
        fields = [
            'id', 'user_trip', 'gtfs_trip', 'starting_stop', 'destination_stop',
            'timezone', 'departure_date', 'departure_time',
            'arrival_date', 'arrival_time', 'duration_in_travel',
            'duration_waiting', 'duration_total',
        ]
        read_only_fields = ['id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            self.fields['user_trip'].queryset = UserTrip.objects.filter(user=request.user)

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['starting_stop'] = _serialize_connection_stop(instance.starting_stop)
        representation['destination_stop'] = _serialize_connection_stop(instance.destination_stop)

        return representation
