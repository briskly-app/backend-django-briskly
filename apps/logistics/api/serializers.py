import zoneinfo

from rest_framework import serializers

from apps.logistics.models import City, Stop


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
            raise serializers.ValidationError('Invalid timezone provided.')
        return value


class StopDestinationQuerySerializer(serializers.Serializer):
    from_stop = serializers.PrimaryKeyRelatedField(queryset=Stop.objects.all())
    date = serializers.DateField()
    time = serializers.TimeField(
        help_text='Search anchor time — earliest moment you are ready to start waiting.',
    )
    waitingTime = serializers.IntegerField(
        min_value=1,
        help_text='Max seconds to wait after search time until the bus departs.',
    )
    timezone = serializers.CharField()
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False, default=50)
    stops_per_city = serializers.IntegerField(
        min_value=1,
        max_value=10,
        required=False,
        default=3,
        help_text='Max destination stops per city (e.g. Centralna and Zachodnia in Warsaw).',
    )

    def validate_timezone(self, value):
        try:
            zoneinfo.ZoneInfo(value)
        except zoneinfo.ZoneInfoNotFoundError:
            raise serializers.ValidationError('Invalid timezone provided.')
        return value


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = [
            'city_id',
            'city_name',
            'city_region_name',
            'city_country_name',
            'city_country_code',
            'city_lat',
            'city_long',
        ]


class CityDetailSerializer(serializers.ModelSerializer):
    description_paragraphs = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )

    class Meta:
        model = City
        fields = [
            'city_id',
            'city_name',
            'city_lat',
            'city_long',
            'city_country_code',
            'city_country_name',
            'city_region_name',
            'city_population',
            'city_timezone',
            'city_thumbnail_url',
            'city_description',
            'description_paragraphs',
        ]


class StopInCitySerializer(serializers.Serializer):
    stop_id = serializers.CharField()
    stop_name = serializers.CharField()
    stop_lat = serializers.FloatField()
    stop_lon = serializers.FloatField()
    suburb = serializers.CharField(allow_null=True)


class CityStopsGroupSerializer(serializers.Serializer):
    city_id = serializers.CharField()
    city_name = serializers.CharField()
    region = serializers.CharField(allow_null=True)
    country_code = serializers.CharField(allow_null=True)
    country_name = serializers.CharField(allow_null=True)
    stops = StopInCitySerializer(many=True)
