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
    city_description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'routes_city'

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

    class Meta:
        db_table = 'routes_place'

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

    class Meta:
        db_table = 'routes_stop'

    def __str__(self):
        return self.stop_name
