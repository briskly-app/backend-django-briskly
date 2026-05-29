from django.contrib import admin

from apps.trips.models import UserTrip, UserTripConnection, UserTripConnectionNote

admin.site.register(UserTrip)
admin.site.register(UserTripConnection)
admin.site.register(UserTripConnectionNote)
