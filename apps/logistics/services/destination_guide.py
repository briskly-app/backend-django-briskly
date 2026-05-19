def pick_best_connection_per_city(results, origin_city_id):
    best_trips_by_city = {}
    for trip in results:
        city_id = trip['destination_stop']['city_id']
        if city_id == origin_city_id:
            continue

        if (
            city_id not in best_trips_by_city
            or trip['duration_total'] < best_trips_by_city[city_id]['duration_total']
        ):
            best_trips_by_city[city_id] = trip

    return list(best_trips_by_city.values())


def sort_and_limit_destinations(connections, limit=50):
    sorted_connections = sorted(
        connections,
        key=lambda x: x['duration_total'] - x['destination_stop']['attraction_score'] / 60,
    )
    return sorted_connections[:limit]
