from django.db import models

class City(models.Model):
    city_id = models.CharField(max_length=100, primary_key=True)
    city_name = models.CharField(max_length=255)
    city_lat = models.FloatField(null=True, blank=True)
    city_long = models.FloatField(null=True, blank=True)
    city_country_code = models.CharField(max_length=2, null=True, blank=True)
    city_country_name = models.CharField(max_length=255, null=True, blank=True)
    city_region_name = models.CharField(max_length=255, null=True, blank=True)
    city_population = models.BigIntegerField(null=True, blank=True)
    city_timezone = models.CharField(max_length=50, null=True, blank=True)
    city_thumbnail_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.city_name

class Place(models.Model):
    place_id = models.CharField(max_length=100, primary_key=True)
    place_name = models.CharField(max_length=255)
    place_display_name = models.CharField(max_length=255, null=True, blank=True)
    place_importance = models.FloatField(null=True, blank=True)
    place_type = models.CharField(max_length=255, null=True, blank=True)
    place_rank = models.IntegerField(null=True, blank=True)
    place_suburb = models.CharField(max_length=255, null=True, blank=True)
    place_city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.place_display_name or self.place_name

class Stop(models.Model):
    stop_id = models.CharField(max_length=100, primary_key=True)
    stop_name = models.CharField(max_length=255)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    stop_code = models.CharField(max_length=5, null=True, blank=True)
    stop_timezone = models.CharField(max_length=50, null=True, blank=True)
    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.stop_name

class Route(models.Model):
    route_id = models.CharField(max_length=100, primary_key=True)
    route_short_name = models.CharField(max_length=50, null=True, blank=True)
    route_long_name = models.CharField(max_length=255, null=True, blank=True)

class Calendar(models.Model):
    service_id = models.CharField(max_length=100, primary_key=True)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()

class Trip(models.Model):
    trip_id = models.CharField(max_length=100, primary_key=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    trip_headsign = models.CharField(max_length=255, null=True, blank=True)
    service = models.ForeignKey(Calendar, on_delete=models.SET_NULL, null=True, blank=True)

class CalendarDate(models.Model):
    service = models.ForeignKey(Calendar, on_delete=models.CASCADE)
    date = models.DateField()
    exception_type = models.IntegerField()

class StopTime(models.Model):
    stop_time_id = models.AutoField(primary_key=True)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    arrival_time = models.CharField(max_length=8)
    departure_time = models.CharField(max_length=8)
    stop_sequence = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=['stop', 'departure_time']),
            models.Index(fields=['trip', 'stop_sequence']),
        ]

class Attraction(models.Model):
    attraction_id = models.CharField(max_length=100, primary_key=True)
    attraction_name = models.CharField(max_length=255)
    attraction_category = models.CharField(max_length=100, null=True, blank=True)
    attraction_lat = models.FloatField()
    attraction_lon = models.FloatField()

    stops = models.ManyToManyField(Stop, through='StopAttraction', related_name='attractions')

class StopAttraction(models.Model):
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    attraction = models.ForeignKey(Attraction, on_delete=models.CASCADE)
    distance_meters = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('stop', 'attraction')