from datetime import datetime, timedelta
import zoneinfo
from .models import Stop, StopTime, Calendar, CalendarDate
import uuid

STATIC_NUMBER_DAYS = 3

def city_description_paragraphs(city):
    if not city or not city.city_description:
        return []
    return [p.strip() for p in city.city_description.split('\n') if p.strip()]

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
            **{day_name: True}
        ).values_list('service_id', flat=True)

        removed = CalendarDate.objects.filter(
            date=curr_date, exception_type=2
        ).values_list('service_id', flat=True)
        
        added = CalendarDate.objects.filter(
            date=curr_date, exception_type=1
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
        trip__service_id__in=valid_service_ids
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
                    'origin_attraction_score': dep.stop.attractions.count(),
                    'origin_city_id': dep.stop.place.place_city.city_id,
                    'origin_city_name': dep.stop.place.place_city.city_name,
                    'origin_city_country_code': dep.stop.place.place_city.city_country_code,
                    'origin_city_country_name': dep.stop.place.place_city.city_country_name,
                    'origin_longitude': dep.stop.stop_lon,
                    'origin_latitude': dep.stop.stop_lat,
                    'service_date': s_date,
                    'departure_time': real_dep_dt
                })

    if not valid_trips:
        return []

    trip_ids = [t['trip_id'] for t in valid_trips]

    destinations = StopTime.objects.filter(
        trip_id__in=trip_ids
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
                    'city_id': dest.stop.place.place_city.city_id,
                    'city_name': dest.stop.place.place_city.city_name,
                    'country_code': dest.stop.place.place_city.city_country_code,
                    'country_name': dest.stop.place.place_city.city_country_name,
                    'attraction_score': dest.stop.attractions.count(),
                    'longitude': dest.stop.stop_lon,
                    'latitude': dest.stop.stop_lat,
                    'thumbnail_url': dest.stop.place.place_city.city_thumbnail_url,
                    'description_paragraphs': city_description_paragraphs(
                        dest.stop.place.place_city
                    ),
                    'suburb': dest.stop.place.place_suburb,
                    'region': dest.stop.place.place_city.city_region_name,
                }
            })

    best_trips_by_city = {}
    for trip in results:
        city_id = trip['destination_stop']['city_id']
        if city_id == city.city_id:
            continue
        
        if city_id not in best_trips_by_city or trip['duration_total'] < best_trips_by_city[city_id]['duration_total']:
            best_trips_by_city[city_id] = trip

    unique_results = list(best_trips_by_city.values())
    unique_results.sort(key=lambda x: x['duration_total'] - x['destination_stop']['attraction_score'] / 60)

    return_connections = unique_results[:50]

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