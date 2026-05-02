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