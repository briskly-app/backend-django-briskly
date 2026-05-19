from django.contrib import admin

from apps.trips.models import UserTrip, UserTripConnection

admin.site.register(UserTrip)
admin.site.register(UserTripConnection)
