from django.db import models

from .location import Stop


class Route(models.Model):
    route_id = models.CharField(max_length=100, primary_key=True)
    route_short_name = models.CharField(max_length=50, null=True, blank=True)
    route_long_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'routes_route'


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

    class Meta:
        db_table = 'routes_calendar'


class Trip(models.Model):
    trip_id = models.CharField(max_length=100, primary_key=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    trip_headsign = models.CharField(max_length=255, null=True, blank=True)
    service = models.ForeignKey(Calendar, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'routes_trip'


class CalendarDate(models.Model):
    service = models.ForeignKey(Calendar, on_delete=models.CASCADE)
    date = models.DateField()
    exception_type = models.IntegerField()

    class Meta:
        db_table = 'routes_calendardate'


class StopTime(models.Model):
    stop_time_id = models.AutoField(primary_key=True)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    arrival_time = models.CharField(max_length=8)
    departure_time = models.CharField(max_length=8)
    stop_sequence = models.IntegerField()

    class Meta:
        db_table = 'routes_stoptime'
        indexes = [
            models.Index(fields=['stop', 'departure_time']),
            models.Index(fields=['trip', 'stop_sequence']),
        ]
