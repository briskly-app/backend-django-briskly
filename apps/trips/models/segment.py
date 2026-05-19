from django.db import models

from apps.trips.models.trip import UserTrip


class UserTripConnection(models.Model):
    user_trip = models.ForeignKey(UserTrip, on_delete=models.CASCADE, related_name='connections')
    gtfs_trip = models.ForeignKey(
        'logistics.Trip', on_delete=models.SET_NULL, null=True, blank=True,
    )

    starting_stop = models.ForeignKey(
        'logistics.Stop', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='started_connections',
    )
    destination_stop = models.ForeignKey(
        'logistics.Stop', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ended_connections',
    )

    timezone = models.CharField(max_length=50)
    departure_date = models.DateField()
    departure_time = models.TimeField()
    arrival_date = models.DateField()
    arrival_time = models.TimeField()

    duration_in_travel = models.IntegerField()
    duration_waiting = models.IntegerField()
    duration_total = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'routes_usertripconnection'
        ordering = ['departure_date', 'departure_time']

    def __str__(self):
        return f"{self.departure_date} | {self.starting_stop} -> {self.destination_stop}"
