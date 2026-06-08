from rest_framework import serializers

from apps.trips.models import UserTrip, UserTripConnection


class UserTripSerializer(serializers.ModelSerializer):
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

        if instance.starting_stop:
            representation['starting_stop'] = {
                'stop_id': instance.starting_stop.stop_id,
                'stop_name': instance.starting_stop.stop_name,
                'city_id': instance.starting_stop.place.place_city.city_id,
                'city_name': instance.starting_stop.place.place_city.city_name,
                'region': instance.starting_stop.place.place_city.city_region_name,
                'longitude': instance.starting_stop.stop_lon,
                'latitude': instance.starting_stop.stop_lat,
                'thumbnail_url': instance.starting_stop.place.place_city.city_thumbnail_url,
            }

        if instance.destination_stop:
            representation['destination_stop'] = {
                'stop_id': instance.destination_stop.stop_id,
                'stop_name': instance.destination_stop.stop_name,
                'city_id': instance.destination_stop.place.place_city.city_id,
                'city_name': instance.destination_stop.place.place_city.city_name,
                'region': instance.destination_stop.place.place_city.city_region_name,
                'longitude': instance.destination_stop.stop_lon,
                'latitude': instance.destination_stop.stop_lat,
                'thumbnail_url': instance.destination_stop.place.place_city.city_thumbnail_url,
            }

        return representation
