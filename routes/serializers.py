from rest_framework import serializers
from .models import City
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