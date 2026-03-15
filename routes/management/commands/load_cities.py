import pandas as pd
import numpy as np
from tqdm import tqdm
from django.core.management.base import BaseCommand
from django.db import transaction
from routes.models import City, Stop

class Command(BaseCommand):
    help = 'Add cities from stops_with_cities.txt and link them to existing stops'

    def handle(self, *args, **kwargs):
        STOPS_FILE = 'gtfs_generic_eu/stops_with_cities.txt'
        CITIES_FILE = 'cities.txt'

        self.stdout.write(self.style.WARNING("Loading stops and cities data..."))

        stops_df = pd.read_csv(STOPS_FILE, dtype={'stop_id': str}, low_memory=False)
        stops_df = stops_df.dropna(subset=['city_id'])
        
        stops_df['city_id'] = stops_df['city_id'].astype(int).astype(str) 
        
        unique_city_ids = stops_df['city_id'].unique()
        self.stdout.write(f"Identified {len(unique_city_ids)} unique cities to add.")

        column_names = [
            'geonameid', 'name', 'asciiname', 'alternatenames', 
            'latitude', 'longitude', 'feature_class', 'feature_code', 
            'country_code', 'cc2', 'admin1_code', 'admin2_code', 
            'admin3_code', 'admin4_code', 'population', 'elevation', 
            'dem', 'timezone', 'modification_date'
        ]
        dtype_settings = {'geonameid': str, 'cc2': str, 'admin1_code': str, 'admin2_code': str, 'admin3_code': str, 'admin4_code': str}
        
        cities_df = pd.read_csv(CITIES_FILE, sep='\t', header=None, names=column_names, dtype=dtype_settings, low_memory=False)
        
        target_cities_df = cities_df[cities_df['geonameid'].isin(unique_city_ids)]
        target_cities_df = target_cities_df.replace({np.nan: None})

        self.stdout.write(self.style.WARNING("2. Saving cities to database..."))
        cities_to_create = []
        
        for _, row in tqdm(target_cities_df.iterrows(), total=len(target_cities_df), desc="Preparing City"):
            city = City(
                city_id=str(row['geonameid']),
                city_name=str(row['name'])[:255],
                city_lat=row['latitude'],
                city_long=row['longitude'],
                city_feature_class=row['feature_class'][:10] if row['feature_class'] else None,
                city_feature_code=row['feature_code'][:10] if row['feature_code'] else None,
                city_country_code=row['country_code'][:2] if row['country_code'] else None,
                city_cc2=row['cc2'][:60] if row['cc2'] else None,
                city_admin1_code=row['admin1_code'][:20] if row['admin1_code'] else None,
                city_admin2_code=row['admin2_code'][:20] if row['admin2_code'] else None,
                city_admin3_code=row['admin3_code'][:20] if row['admin3_code'] else None,
                city_admin4_code=row['admin4_code'][:20] if row['admin4_code'] else None,
                city_population=int(row['population']) if row['population'] is not None else 0,
                city_timezone=row['timezone'][:50] if row['timezone'] else None,
            )
            cities_to_create.append(city)

        with transaction.atomic():
            City.objects.bulk_create(cities_to_create, batch_size=1000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS('Cities saved!'))

        self.stdout.write(self.style.WARNING("3. Linking existing stops to cities..."))
        
        stop_city_mapping = dict(zip(stops_df['stop_id'], stops_df['city_id']))
        
        stops_in_db = Stop.objects.filter(stop_id__in=stop_city_mapping.keys())
        
        stops_to_update = []
        for stop in tqdm(stops_in_db, total=stops_in_db.count(), desc="Linking cities to stops"):
            city_id = stop_city_mapping.get(stop.stop_id)
            if city_id:
                stop.city_id = city_id
                stops_to_update.append(stop)

        with transaction.atomic():
            Stop.objects.bulk_update(stops_to_update, ['city_id'], batch_size=1000)
            
        self.stdout.write(self.style.SUCCESS(f'Linked {len(stops_to_update)} stops to cities!'))