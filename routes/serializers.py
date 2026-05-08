from rest_framework import serializers
from .models import City, UserTrip, UserTripConnection
import zoneinfo

class DestinationQuerySerializer(serializers.Serializer):
    from_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    date = serializers.DateField()
    time = serializers.TimeField()
    waitingTime = serializers.IntegerField(min_value=1)
    timezone = serializers.CharField()

    def validate_timezone(self, value):
        try:
            zoneinfo.ZoneInfo(value)
        except zoneinfo.ZoneInfoNotFoundError:
            raise serializers.ValidationError("Invalid timezone provided.")
        return value

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['city_id', 'city_name', 'city_region_name', 'city_country_name', 'city_country_code']

class UserTripSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTrip
        fields = ['slug', 'name', 'start_date', 'end_date', 'thumbnail_url', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

class UserTripConnectionSerializer(serializers.ModelSerializer):

    user_trip = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=UserTrip.objects.all()
    )

    class Meta:
        model = UserTripConnection
        fields = [
            'id', 'user_trip', 'gtfs_trip', 'starting_stop', 'destination_stop',
            'timezone', 'departure_date', 'departure_time',
            'arrival_date', 'arrival_time', 'duration_in_travel',
            'duration_waiting', 'duration_total'
        ]
        read_only_fields = ['id']

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