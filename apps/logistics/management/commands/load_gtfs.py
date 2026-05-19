import os
import pandas as pd
from datetime import datetime
from django.core.management.base import BaseCommand
from apps.logistics.models import Stop, Route, Trip, StopTime, Calendar, CalendarDate

class Command(BaseCommand):
    help = 'Loading GTFS data from a specified folder into the database'

    def add_arguments(self, parser):
        parser.add_argument('folder_path', type=str, help='Path to the folder containing GTFS files')

    def parse_date(self, date_str):
        if not date_str or pd.isna(date_str):
            return None
        date_str = str(date_str).strip().split('.')[0]
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    def handle(self, *args, **kwargs):
        folder_path = kwargs['folder_path']
        batch_size = 5000
        self.stdout.write(self.style.SUCCESS(f'Starting loading from: {folder_path}'))

        calendar_path = os.path.join(folder_path, 'calendar.txt')
        existing_services = set()
        
        if os.path.exists(calendar_path):
            self.stdout.write('Loading Calendar...')
            df_cal = pd.read_csv(calendar_path, dtype=str).fillna('')
            calendars_to_create = []
            
            for _, row in df_cal.iterrows():
                service_id = row['service_id']
                existing_services.add(service_id)
                calendars_to_create.append(Calendar(
                    service_id=service_id,
                    monday=(row['monday'] == '1'),
                    tuesday=(row['tuesday'] == '1'),
                    wednesday=(row['wednesday'] == '1'),
                    thursday=(row['thursday'] == '1'),
                    friday=(row['friday'] == '1'),
                    saturday=(row['saturday'] == '1'),
                    sunday=(row['sunday'] == '1'),
                    start_date=self.parse_date(row['start_date']),
                    end_date=self.parse_date(row['end_date'])
                ))
            Calendar.objects.bulk_create(calendars_to_create, batch_size=batch_size, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f'Completed Calendar: {len(calendars_to_create)} records.'))

        cal_dates_path = os.path.join(folder_path, 'calendar_dates.txt')
        if os.path.exists(cal_dates_path):
            self.stdout.write('Loading Calendar Dates...')
            df_cal_dates = pd.read_csv(cal_dates_path, dtype=str).fillna('')
            
            missing_services = set(df_cal_dates['service_id']) - existing_services
            if missing_services:
                self.stdout.write(self.style.WARNING(f'Found {len(missing_services)} missing service_id(s). Creating dummy calendars...'))
                dummy_calendars = [
                    Calendar(
                        service_id=srv_id, 
                        start_date='2000-01-01',
                        end_date='2099-12-31'
                    ) for srv_id in missing_services
                ]
                Calendar.objects.bulk_create(dummy_calendars, batch_size=batch_size, ignore_conflicts=True)
                existing_services.update(missing_services)

            cal_dates_to_create = []
            for _, row in df_cal_dates.iterrows():
                cal_dates_to_create.append(CalendarDate(
                    service_id=row['service_id'],
                    date=self.parse_date(row['date']),
                    exception_type=int(row['exception_type'])
                ))
            CalendarDate.objects.bulk_create(cal_dates_to_create, batch_size=batch_size, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f'Completed Calendar Dates: {len(cal_dates_to_create)} records.'))

        self.stdout.write('Loading Stops...')
        df_stops = pd.read_csv(os.path.join(folder_path, 'stops.txt'), dtype=str).fillna('')
        stops_to_create = []
        for _, row in df_stops.iterrows():
            stops_to_create.append(Stop(
                stop_id=row['stop_id'],
                stop_name=row['stop_name'],
                stop_lat=float(row['stop_lat']) if row['stop_lat'] else 0.0,
                stop_lon=float(row['stop_lon']) if row['stop_lon'] else 0.0,
                stop_code=row.get('stop_code', ''),
                stop_timezone=row.get('stop_timezone', '')
            ))
        Stop.objects.bulk_create(stops_to_create, batch_size=batch_size, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'Completed Stops: {len(stops_to_create)} records.'))

        self.stdout.write('Loading Routes...')
        df_routes = pd.read_csv(os.path.join(folder_path, 'routes.txt'), dtype=str).fillna('')
        routes_to_create = []
        for _, row in df_routes.iterrows():
            routes_to_create.append(Route(
                route_id=row['route_id'],
                route_short_name=row['route_short_name'],
                route_long_name=row['route_long_name']
            ))
        Route.objects.bulk_create(routes_to_create, batch_size=batch_size, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'Completed Routes: {len(routes_to_create)} records.'))

        self.stdout.write('Loading Trips...')
        df_trips = pd.read_csv(os.path.join(folder_path, 'trips.txt'), dtype=str).fillna('')
        trips_to_create = []
        for _, row in df_trips.iterrows():
            trips_to_create.append(Trip(
                trip_id=row['trip_id'],
                route_id=row['route_id'], 
                trip_headsign=row.get('trip_headsign', ''),
                service_id=row['service_id'] if row['service_id'] in existing_services else None
            ))
        Trip.objects.bulk_create(trips_to_create, batch_size=batch_size, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'Completed Trips: {len(trips_to_create)} records.'))

        self.stdout.write('Loading StopTimes...')
        df_stop_times = pd.read_csv(os.path.join(folder_path, 'stop_times.txt'), dtype=str).fillna('')
        stop_times_to_create = []
        
        for _, row in df_stop_times.iterrows():
            stop_times_to_create.append(StopTime(
                trip_id=row['trip_id'],
                stop_id=row['stop_id'],
                arrival_time=row['arrival_time'],
                departure_time=row['departure_time'],
                stop_sequence=int(row['stop_sequence'])
            ))
        StopTime.objects.bulk_create(stop_times_to_create, batch_size=batch_size, ignore_conflicts=True)
        
        self.stdout.write(self.style.SUCCESS(f'Completed Stop Times: {len(stop_times_to_create)} records.'))