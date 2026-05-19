class TripCompletionError(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def complete_user_trip(trip):
    connections = trip.connections.all()

    if not connections.exists():
        raise TripCompletionError("Cannot complete an empty trip.")

    trip.start_date = connections.first().departure_date
    trip.end_date = connections.last().arrival_date

    visited_cities = []

    for connection in connections:
        start_city = connection.starting_stop.place.place_city
        end_city = connection.destination_stop.place.place_city

        if start_city not in visited_cities:
            visited_cities.append(start_city)
        if end_city not in visited_cities:
            visited_cities.append(end_city)

    unique_countries = set()
    unique_regions = set()

    current_population = 0

    for city in visited_cities:
        if city.city_thumbnail_url and current_population < city.city_population:
            trip.thumbnail_url = city.city_thumbnail_url
            current_population = city.city_population

        if city.city_country_name not in unique_countries:
            unique_countries.add(city.city_country_name)
        if city.city_region_name not in unique_regions:
            unique_regions.add(city.city_region_name)

    name_elements = []

    if len(visited_cities) <= 2:
        name_elements = [c.city_name for c in visited_cities]
    elif len(unique_countries) > 1:
        name_elements = list(unique_countries)
    elif len(unique_regions) > 1:
        name_elements = list(unique_regions)
    else:
        name_elements = [c.city_name for c in visited_cities]

    if len(name_elements) > 3:
        middle_index = len(name_elements) // 2
        final_name_parts = [
            name_elements[0],
            name_elements[middle_index],
            name_elements[-1],
        ]
    else:
        final_name_parts = name_elements

    if len(final_name_parts) == 3:
        trip.name = f"{final_name_parts[0]}, {final_name_parts[1]} and {final_name_parts[2]}"
    elif len(final_name_parts) == 2:
        trip.name = f"{final_name_parts[0]} and {final_name_parts[1]}"
    else:
        trip.name = final_name_parts[0]

    trip.save()
    return trip
