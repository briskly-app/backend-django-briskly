from datetime import datetime, timedelta
import uuid
import zoneinfo

from django.db.models import Count

from apps.logistics.models import Stop, StopTime, Calendar, CalendarDate
from apps.logistics.services.attractiveness import (
    attraction_score_for_stop,
    city_description_paragraphs,
)
from apps.logistics.services.destination_guide import (
    limit_connections_per_destination_city,
    pick_best_connection_per_city,
    pick_best_connection_per_stop,
    sort_and_limit_by_attractiveness,
    sort_and_limit_destinations,
)

STATIC_NUMBER_DAYS = 3


def parse_gtfs_time(gtfs_time_str):
    h, m, s = map(int, gtfs_time_str.split(':'))
    return timedelta(hours=h, minutes=m, seconds=s)


def get_real_datetime(base_date, gtfs_time_str, tz_name):
    tz = zoneinfo.ZoneInfo(tz_name)
    td = parse_gtfs_time(gtfs_time_str)
    real_dt = datetime.combine(base_date, datetime.min.time()) + td
    return real_dt.replace(tzinfo=tz)


def get_service_dates_map(begin_date, end_date):
    service_dates = {}
    delta = end_date - begin_date

    for i in range(delta.days + 1):
        curr_date = begin_date + timedelta(days=i)
        day_name = curr_date.strftime('%A').lower()

        cals = Calendar.objects.filter(
            start_date__lte=curr_date,
            end_date__gte=curr_date,
            **{day_name: True},
        ).values_list('service_id', flat=True)

        removed = CalendarDate.objects.filter(
            date=curr_date, exception_type=2,
        ).values_list('service_id', flat=True)

        added = CalendarDate.objects.filter(
            date=curr_date, exception_type=1,
        ).values_list('service_id', flat=True)

        active = (set(cals) - set(removed)) | set(added)

        for s_id in active:
            if s_id not in service_dates:
                service_dates[s_id] = []
            service_dates[s_id].append(curr_date)

    return service_dates


def find_direct_connections(city, req_date, req_time, waiting_time, tz_name):
    tz = zoneinfo.ZoneInfo(tz_name)
    user_start_dt = datetime.combine(req_date, req_time).replace(tzinfo=tz)
    user_end_dt = user_start_dt + timedelta(seconds=waiting_time)

    begin_date = req_date - timedelta(days=STATIC_NUMBER_DAYS)
    end_date = req_date + timedelta(days=STATIC_NUMBER_DAYS)

    service_dates = get_service_dates_map(begin_date, end_date)
    valid_service_ids = list(service_dates.keys())

    origin_stops = Stop.objects.filter(place__place_city=city)

    departures = StopTime.objects.filter(
        stop__in=origin_stops,
        trip__service_id__in=valid_service_ids,
    ).select_related('trip', 'stop__place__place_city')

    valid_trips = []

    for dep in departures:
        dates_active = service_dates.get(dep.trip.service_id, [])
        for s_date in dates_active:
            real_dep_dt = get_real_datetime(s_date, dep.departure_time, tz_name)

            if user_start_dt <= real_dep_dt <= user_end_dt:
                valid_trips.append({
                    'trip_id': dep.trip_id,
                    'origin_stop_sequence': dep.stop_sequence,
                    'origin_stop_id': dep.stop.stop_id,
                    'origin_stop_name': dep.stop.stop_name,
                    'origin_attraction_score': attraction_score_for_stop(dep.stop),
                    'origin_city_id': dep.stop.place.place_city.city_id,
                    'origin_city_name': dep.stop.place.place_city.city_name,
                    'origin_city_country_code': dep.stop.place.place_city.city_country_code,
                    'origin_city_country_name': dep.stop.place.place_city.city_country_name,
                    'origin_longitude': dep.stop.stop_lon,
                    'origin_latitude': dep.stop.stop_lat,
                    'service_date': s_date,
                    'departure_time': real_dep_dt,
                })

    if not valid_trips:
        return []

    trip_ids = [t['trip_id'] for t in valid_trips]

    destinations = StopTime.objects.filter(
        trip_id__in=trip_ids,
    ).select_related('stop__place__place_city')

    destinations_by_trip = {}
    for dest in destinations:
        if dest.trip_id not in destinations_by_trip:
            destinations_by_trip[dest.trip_id] = []
        destinations_by_trip[dest.trip_id].append(dest)

    results = []

    for valid_trip in valid_trips:
        trip_dests = [
            d for d in destinations_by_trip.get(valid_trip['trip_id'], [])
            if d.stop_sequence > valid_trip['origin_stop_sequence']
        ]

        for dest in trip_dests:
            arr_dt = get_real_datetime(valid_trip['service_date'], dest.arrival_time, tz_name)
            travel_sec = (arr_dt - valid_trip['departure_time']).total_seconds()
            waiting_sec = (valid_trip['departure_time'] - user_start_dt).total_seconds()
            total_sec = waiting_sec + travel_sec

            dest_city = dest.stop.place.place_city
            results.append({
                'id': uuid.uuid4(),
                'trip_id': valid_trip['trip_id'],
                'departure_date': valid_trip['departure_time'].strftime('%Y-%m-%d'),
                'departure_time': valid_trip['departure_time'].strftime('%H:%M'),
                'arrival_date': arr_dt.strftime('%Y-%m-%d'),
                'arrival_time': arr_dt.strftime('%H:%M'),
                'duration_in_travel': travel_sec,
                'duration_waiting': waiting_sec,
                'duration_total': total_sec,
                'starting_stop': {
                    'stop_id': valid_trip['origin_stop_id'],
                    'stop_name': valid_trip['origin_stop_name'],
                    'city_id': valid_trip['origin_city_id'],
                    'city_name': valid_trip['origin_city_name'],
                    'country_code': valid_trip['origin_city_country_code'],
                    'country_name': valid_trip['origin_city_country_name'],
                    'attraction_score': valid_trip['origin_attraction_score'],
                    'longitude': valid_trip['origin_longitude'],
                    'latitude': valid_trip['origin_latitude'],
                },
                'destination_stop': {
                    'stop_id': dest.stop.stop_id,
                    'stop_name': dest.stop.stop_name,
                    'city_id': dest_city.city_id,
                    'city_name': dest_city.city_name,
                    'country_code': dest_city.city_country_code,
                    'country_name': dest_city.city_country_name,
                    'attraction_score': attraction_score_for_stop(dest.stop),
                    'longitude': dest.stop.stop_lon,
                    'latitude': dest.stop.stop_lat,
                    'thumbnail_url': dest_city.city_thumbnail_url,
                    'description_paragraphs': city_description_paragraphs(dest_city),
                    'suburb': dest.stop.place.place_suburb,
                    'region': dest_city.city_region_name,
                },
            })

    unique_results = pick_best_connection_per_city(results, city.city_id)
    return_connections = sort_and_limit_destinations(unique_results)

    return {
        'count': len(return_connections),
        'city_id': city.city_id,
        'city_name': city.city_name,
        'region': city.city_region_name,
        'country_code': city.city_country_code,
        'country_name': city.city_country_name,
        'search_date': req_date.strftime('%Y-%m-%d'),
        'search_time': req_time.strftime('%H:%M'),
        'timezone': tz_name,
        'results': return_connections,
    }


def _collect_valid_departures(origin_stop, valid_service_ids, service_dates, user_start_dt, user_end_dt, tz_name):
    departures = StopTime.objects.filter(
        stop=origin_stop,
        trip__service_id__in=valid_service_ids,
    ).select_related('trip')

    valid_trips = []
    for dep in departures:
        dates_active = service_dates.get(dep.trip.service_id, [])
        for s_date in dates_active:
            real_dep_dt = get_real_datetime(s_date, dep.departure_time, tz_name)
            if user_start_dt <= real_dep_dt <= user_end_dt:
                valid_trips.append({
                    'trip_id': dep.trip_id,
                    'origin_stop_sequence': dep.stop_sequence,
                    'service_date': s_date,
                    'departure_time': real_dep_dt,
                })
    return valid_trips


def _build_stop_and_city_lookup(stop_ids):
    stops_qs = Stop.objects.filter(
        stop_id__in=stop_ids,
    ).select_related('place__place_city').annotate(
        attraction_score=Count('attractions'),
    )

    stops_dict = {}
    cities_dict = {}

    for stop in stops_qs:
        city = stop.place.place_city if stop.place else None
        stops_dict[stop.stop_id] = {
            'stop_id': stop.stop_id,
            'stop_name': stop.stop_name,
            'lat': stop.stop_lat,
            'lon': stop.stop_lon,
            'city_id': city.city_id if city else None,
            'suburb': stop.place.place_suburb if stop.place else None,
            'attraction_score': stop.attraction_score,
        }
        if city and city.city_id not in cities_dict:
            cities_dict[city.city_id] = {
                'city_id': city.city_id,
                'city_name': city.city_name,
                'region': city.city_region_name,
                'country_code': city.city_country_code,
                'country_name': city.city_country_name,
                'thumbnail_url': city.city_thumbnail_url,
            }

    return stops_dict, cities_dict


def find_direct_connections_from_stop(
    origin_stop,
    req_date,
    req_time,
    waiting_time,
    tz_name,
    *,
    result_limit=50,
    stops_per_city=3,
):
    tz = zoneinfo.ZoneInfo(tz_name)
    user_start_dt = datetime.combine(req_date, req_time).replace(tzinfo=tz)
    user_end_dt = user_start_dt + timedelta(seconds=waiting_time)

    begin_date = req_date - timedelta(days=STATIC_NUMBER_DAYS)
    end_date = req_date + timedelta(days=STATIC_NUMBER_DAYS)

    service_dates = get_service_dates_map(begin_date, end_date)
    valid_service_ids = list(service_dates.keys())

    valid_trips = _collect_valid_departures(
        origin_stop,
        valid_service_ids,
        service_dates,
        user_start_dt,
        user_end_dt,
        tz_name,
    )

    origin_city = origin_stop.place.place_city if origin_stop.place else None

    if not valid_trips:
        return {
            'count': 0,
            'search': {
                'from_stop_id': origin_stop.stop_id,
                'date': req_date.strftime('%Y-%m-%d'),
                'time': req_time.strftime('%H:%M'),
                'waiting_time_seconds': int(waiting_time),
                'timezone': tz_name,
            },
            'origin': {
                'stop_id': origin_stop.stop_id,
                'stop_name': origin_stop.stop_name,
                'city_id': origin_city.city_id if origin_city else None,
            },
            'connections': [],
            'stops': {},
            'cities': {},
        }

    trip_ids = [t['trip_id'] for t in valid_trips]

    destinations = StopTime.objects.filter(
        trip_id__in=trip_ids,
    ).select_related('stop__place__place_city')

    destinations_by_trip = {}
    for dest in destinations:
        destinations_by_trip.setdefault(dest.trip_id, []).append(dest)

    raw_results = []

    for valid_trip in valid_trips:
        trip_dests = [
            d for d in destinations_by_trip.get(valid_trip['trip_id'], [])
            if d.stop_sequence > valid_trip['origin_stop_sequence']
        ]

        for dest in trip_dests:
            dest_city = dest.stop.place.place_city if dest.stop.place else None
            if not dest_city:
                continue
            if origin_city and dest_city.city_id == origin_city.city_id:
                continue

            arr_dt = get_real_datetime(valid_trip['service_date'], dest.arrival_time, tz_name)
            travel_sec = (arr_dt - valid_trip['departure_time']).total_seconds()
            waiting_sec = (valid_trip['departure_time'] - user_start_dt).total_seconds()
            total_sec = waiting_sec + travel_sec

            bus_departure = valid_trip['departure_time']
            raw_results.append({
                'id': str(uuid.uuid4()),
                'trip_id': valid_trip['trip_id'],
                'departure_date': bus_departure.strftime('%Y-%m-%d'),
                'departure_time': bus_departure.strftime('%H:%M'),
                'departure_at': bus_departure.isoformat(),
                'arrival_date': arr_dt.strftime('%Y-%m-%d'),
                'arrival_time': arr_dt.strftime('%H:%M'),
                'arrival_at': arr_dt.isoformat(),
                'duration_in_travel': int(travel_sec),
                'duration_waiting': int(waiting_sec),
                'duration_total': int(total_sec),
                'destination_stop_id': dest.stop.stop_id,
                'destination_city_id': dest_city.city_id,
            })

    unique_results = pick_best_connection_per_stop(raw_results, origin_stop.stop_id)

    stop_ids = {origin_stop.stop_id}
    for conn in unique_results:
        stop_ids.add(conn['destination_stop_id'])

    stops_dict, cities_dict = _build_stop_and_city_lookup(stop_ids)

    for conn in unique_results:
        dest_stop = stops_dict.get(conn['destination_stop_id'], {})
        conn['attraction_score'] = dest_stop.get('attraction_score', 0)
        conn['destination_city_id'] = conn.get('destination_city_id') or dest_stop.get('city_id')

    per_city_cap = min(max(int(stops_per_city), 1), 10)
    origin_city_id = origin_city.city_id if origin_city else None
    city_limited = limit_connections_per_destination_city(
        unique_results,
        origin_city_id=origin_city_id,
        max_stops_per_city=per_city_cap,
    )

    limited_connections = sort_and_limit_by_attractiveness(city_limited, limit=result_limit)

    for conn in limited_connections:
        conn.pop('attraction_score', None)

    return {
        'count': len(limited_connections),
        'search': {
            'from_stop_id': origin_stop.stop_id,
            'date': req_date.strftime('%Y-%m-%d'),
            'time': req_time.strftime('%H:%M'),
            'waiting_time_seconds': int(waiting_time),
            'timezone': tz_name,
        },
        'origin': {
            'stop_id': origin_stop.stop_id,
            'stop_name': origin_stop.stop_name,
            'city_id': origin_city.city_id if origin_city else None,
        },
        'connections': limited_connections,
        'stops': stops_dict,
        'cities': cities_dict,
    }
