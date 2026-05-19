from django.db import models

from .location import Stop


class Attraction(models.Model):
    attraction_id = models.CharField(max_length=100, primary_key=True)
    attraction_name = models.CharField(max_length=255)
    attraction_category = models.CharField(max_length=100, null=True, blank=True)
    attraction_lat = models.FloatField()
    attraction_lon = models.FloatField()

    stops = models.ManyToManyField(Stop, through='StopAttraction', related_name='attractions')

    class Meta:
        db_table = 'routes_attraction'


class StopAttraction(models.Model):
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    attraction = models.ForeignKey(Attraction, on_delete=models.CASCADE)
    distance_meters = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'routes_stopattraction'
        unique_together = ('stop', 'attraction')
