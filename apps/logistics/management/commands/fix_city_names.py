import pandas as pd
from tqdm import tqdm
import logging
import unicodedata
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.logistics.models import City

logger = logging.getLogger('fix_city_names')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('fix_city_names.log', encoding='utf-8')
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
    help = 'Fix city names and population data for cities with missing population information using cities.txt database'

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

        cities_to_process = City.objects.filter(city_population=0)
        total_cities = cities_to_process.count()
        
        logger.info(f"Found {total_cities} cities to process.")
        if total_cities == 0:
            return

        for city in tqdm(cities_to_process, total=total_cities, desc="Updating Cities"):
            
            city_id = city.city_id
            city_name = city.city_name
            country_code = city.city_country_code
            
            match = df_cities[
                (df_cities['normalized_name'] == normalize_to_ascii(city_name)) & 
                (df_cities['country_code'] == country_code)
            ]

            population = 0
            timezone = None

            if not match.empty:
                best_match = match.sort_values('population', ascending=False).iloc[0]
                population = int(best_match['population'])
            else:
                logger.warning(f"No city match found for city {city.city_id} with city name '{city_name}' and country code '{country_code}'")

            with transaction.atomic():
                city_obj, created = City.objects.update_or_create(
                    city_id=city_id,
                    defaults={
                        'city_name': city_name[:255],
                        'city_population': population
                    }
                )

                logger.info(f"Updated city {city_obj.city_name} with population {population} and timezone {timezone}")

        logger.info("Completed city updates.")