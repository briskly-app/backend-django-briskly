def city_description_paragraphs(city):
    if not city or not city.city_description:
        return []
    return [p.strip() for p in city.city_description.split('\n') if p.strip()]


def attraction_score_for_stop(stop):
    return stop.attractions.count()
