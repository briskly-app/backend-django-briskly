from django.contrib import admin

from apps.logistics.models import (
    Attraction,
    Calendar,
    CalendarDate,
    City,
    Place,
    Route,
    Stop,
    StopAttraction,
    StopTime,
    Trip,
)

admin.site.register(City)
admin.site.register(Place)
admin.site.register(Stop)
admin.site.register(Route)
admin.site.register(Calendar)
admin.site.register(Trip)
admin.site.register(CalendarDate)
admin.site.register(StopTime)
admin.site.register(Attraction)
admin.site.register(StopAttraction)
