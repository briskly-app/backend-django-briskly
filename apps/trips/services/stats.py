from apps.trips.models import UserTrip, UserTripConnection, UserTripConnectionNote


def build_user_dashboard_stats(user):
    trips = UserTrip.objects.filter(user=user)
    connections = UserTripConnection.objects.filter(user_trip__user=user)
    notes = UserTripConnectionNote.objects.filter(
        user_trip_connection__user_trip__user=user,
    )

    finalized_trips = trips.filter(start_date__isnull=False, end_date__isnull=False).count()
    total_travel_seconds = sum(
        connections.values_list('duration_in_travel', flat=True),
    )
    total_kilometers = round(total_travel_seconds / 3600 * 80)

    countries = set()
    for connection in connections.select_related(
        'starting_stop__place__place_city',
        'destination_stop__place__place_city',
    ):
        for stop in (connection.starting_stop, connection.destination_stop):
            city = stop.place.place_city
            if city.city_country_name:
                countries.add(city.city_country_name)

    photos_taken = notes.exclude(image_url='').count()

    return {
        'countries_visited': len(countries),
        'countries_delta': '',
        'total_kilometers': f'{total_kilometers} km',
        'kilometers_delta': '',
        'expeditions': finalized_trips,
        'expeditions_delta': '',
        'photos_taken': photos_taken,
        'daily_pace': '—',
        'temperature': '—',
        'altitude': '—',
        'trips_total': trips.count(),
    }
