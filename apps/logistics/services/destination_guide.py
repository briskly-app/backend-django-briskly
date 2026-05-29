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


def pick_best_connection_per_stop(results, origin_stop_id):
    best_trips_by_stop = {}
    for trip in results:
        dest_stop_id = trip['destination_stop_id']
        if dest_stop_id == origin_stop_id:
            continue

        if (
            dest_stop_id not in best_trips_by_stop
            or trip['duration_total'] < best_trips_by_stop[dest_stop_id]['duration_total']
        ):
            best_trips_by_stop[dest_stop_id] = trip

    return list(best_trips_by_stop.values())


def _connection_attraction_score(connection):
    if 'attraction_score' in connection:
        return connection['attraction_score']
    return connection.get('destination_stop', {}).get('attraction_score', 0)


def sort_and_limit_destinations(connections, limit=50):
    sorted_connections = sorted(
        connections,
        key=lambda x: x['duration_total'] - _connection_attraction_score(x) / 60,
    )
    return sorted_connections[:limit]


def sort_and_limit_by_attractiveness(connections, limit=50):
    sorted_connections = sorted(
        connections,
        key=lambda x: (-_connection_attraction_score(x), x['duration_total']),
    )
    return sorted_connections[:limit]


def limit_connections_per_destination_city(
    connections,
    *,
    origin_city_id,
    max_stops_per_city,
):
    """Keep up to N best connections per destination city (by attractiveness, then duration)."""
    by_city = {}
    city_order = []

    for conn in connections:
        city_id = conn.get('destination_city_id')
        if not city_id or city_id == origin_city_id:
            continue

        if city_id not in by_city:
            city_order.append(city_id)
            by_city[city_id] = []

        by_city[city_id].append(conn)

    output = []
    for city_id in city_order:
        city_conns = sorted(
            by_city[city_id],
            key=lambda x: (-_connection_attraction_score(x), x['duration_total']),
        )
        output.extend(city_conns[:max_stops_per_city])

    return output
