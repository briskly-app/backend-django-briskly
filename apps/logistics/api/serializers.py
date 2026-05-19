import zoneinfo

from rest_framework import serializers

from apps.logistics.models import City


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
        fields = [
            'city_id', 'city_name', 'city_region_name',
            'city_country_name', 'city_country_code',
        ]
