from django.db.models import Q

from apps.logistics.models import Stop

MAX_CITY_GROUPS = 10
MAX_STOPS_PER_CITY = 10


def search_stops_grouped_by_city(search_query, *, city_limit=10, stops_per_city=5):
    city_limit = min(max(city_limit, 1), MAX_CITY_GROUPS)
    stops_per_city = min(max(stops_per_city, 1), MAX_STOPS_PER_CITY)

    stops = Stop.objects.filter(
        Q(stop_name__icontains=search_query)
        | Q(place__place_city__city_name__icontains=search_query)
        | Q(place__place_suburb__icontains=search_query)
        | Q(place__place_city__city_region_name__icontains=search_query)
        | Q(place__place_city__city_country_name__icontains=search_query),
    ).select_related('place__place_city').order_by(
        '-place__place_city__city_population',
        'stop_name',
    )

    groups = {}
    city_order = []

    for stop in stops:
        if not stop.place or not stop.place.place_city:
            continue

        city = stop.place.place_city
        city_id = city.city_id

        if city_id not in groups:
            if len(city_order) >= city_limit:
                continue
            city_order.append(city_id)
            groups[city_id] = {
                'city_id': city.city_id,
                'city_name': city.city_name,
                'region': city.city_region_name,
                'country_code': city.city_country_code,
                'country_name': city.city_country_name,
                'stops': [],
            }

        if len(groups[city_id]['stops']) >= stops_per_city:
            continue

        groups[city_id]['stops'].append({
            'stop_id': stop.stop_id,
            'stop_name': stop.stop_name,
            'stop_lat': stop.stop_lat,
            'stop_lon': stop.stop_lon,
            'suburb': stop.place.place_suburb,
        })

    return [groups[city_id] for city_id in city_order]
