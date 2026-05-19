import time
import requests
import pandas as pd
from tqdm import tqdm
import logging
import unicodedata
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.logistics.models import City, Place, Stop

logger = logging.getLogger('seed_places')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('seed_places.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def normalize_to_ascii(text):
    if not isinstance(text, str):
        return ""
    text = text.replace('ł', 'l').replace('Ł', 'L')
    return ''.join(c for c in unicodedata.normalize('NFKD', text) 
                   if unicodedata.category(c) != 'Mn').lower().strip()

class Command(BaseCommand):
    help = 'Load data from cities.txt and enrich stops with city and place information using Nominatim API'

    def handle(self, *args, **kwargs):
        CITIES_FILE = 'cities.txt' 
        
        logger.info("Loading city database into memory...")
        
        column_names = [
            'geonameid', 'name', 'asciiname', 'alternatenames', 
            'latitude', 'longitude', 'feature_class', 'feature_code', 
            'country_code', 'cc2', 'admin1_code', 'admin2_code', 
            'admin3_code', 'admin4_code', 'population', 'elevation', 
            'dem', 'timezone', 'modification_date'
        ]
        dtype_settings = {'geonameid': str, 'country_code': str}
        
        try:
            df_cities = pd.read_csv(CITIES_FILE, sep='\t', header=None, names=column_names, dtype=dtype_settings, low_memory=False)
            df_cities['normalized_name'] = df_cities['name'].apply(normalize_to_ascii)
        except Exception as e:
            logger.error(f"Error loading cities.txt file: {e}")
            return

        stops_to_process = Stop.objects.filter(place__isnull=True)
        total_stops = stops_to_process.count()
        
        logger.info(f"Found {total_stops} stops to process.")
        if total_stops == 0:
            return

        headers = {'User-Agent': 'BrisklyApp/1.0 (demo@email.com)'}

        for stop in tqdm(stops_to_process, total=total_stops, desc="Geocoding"):
            time.sleep(1.1)

            url = f"https://nominatim.openstreetmap.org/reverse?lat={stop.stop_lat}&lon={stop.stop_lon}&format=json&accept-language=en"
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    continue
                data = response.json()
            except Exception as e:
                logger.error(f"Error occurred while fetching data for stop {stop.stop_id}: {e}")
                continue
                
            if 'error' in data:
                continue

            address = data.get('address', {})
            
            city_name = address.get('city') or address.get('town') or address.get('village') or address.get('municipality', 'Unknown')
            country_code = address.get('country_code', '').upper()
            
            match = df_cities[
                (df_cities['normalized_name'] == normalize_to_ascii(city_name)) & 
                (df_cities['country_code'] == country_code)
            ]

            city_id = f"custom_{city_name}_{country_code}"
            population = 0
            timezone = None

            if not match.empty:
                best_match = match.sort_values('population', ascending=False).iloc[0]
                city_id = str(best_match['geonameid'])
                population = int(best_match['population'])
                timezone = best_match['timezone']
            else:
                logger.warning(f"No city match found for stop {stop.stop_id} with city name '{city_name}' and country code '{country_code}'")

            with transaction.atomic():
                city_obj, created = City.objects.update_or_create(
                    city_id=city_id,
                    defaults={
                        'city_name': city_name[:255],
                        'city_lat': float(data.get('lat', 0)),
                        'city_long': float(data.get('lon', 0)),
                        'city_country_code': country_code[:2],
                        'city_country_name': address.get('country', '')[:255],
                        'city_region_name': address.get('state', '')[:255],
                        'city_population': population,
                        'city_timezone': timezone,
                        'city_thumbnail_url': None
                    }
                )

                place_id = str(data.get('place_id', f"osm_{data.get('osm_id', stop.stop_id)}"))
                
                place_obj, created = Place.objects.update_or_create(
                    place_id=place_id,
                    defaults={
                        'place_name': data.get('name', city_name)[:255],
                        'place_display_name': data.get('display_name', '')[:255],
                        'place_importance': data.get('importance'),
                        'place_type': data.get('type', '')[:255],
                        'place_rank': data.get('place_rank'),
                        'place_suburb': address.get('suburb', '')[:255],
                        'place_city': city_obj
                    }
                )

                stop.place = place_obj 
                stop.save(update_fields=['place', 'stop_timezone'])
                logger.info(f"Updated stop {stop.stop_name} with place {place_obj.place_display_name} and city {city_obj.city_name}")

        logger.info("Completed geocoding and city assignment for all stops.")