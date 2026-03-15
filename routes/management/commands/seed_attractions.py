import time
import math
import requests
import threading
import queue
import logging
from tqdm import tqdm
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from routes.models import Stop, Attraction, StopAttraction

logger = logging.getLogger('osm_seeder')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('seed_osm.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 4 Servers = 4 Workers
OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter"
]

def get_distance(lat1, lon1, lat2, lon2):
    """Calculates distance in meters (Haversine formula) using the standard math library."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

class Command(BaseCommand):
    help = 'Multi-threaded fetching of attractions with a progress bar'

    def handle(self, *args, **kwargs):
        # Find only the stops that DO NOT have attractions assigned yet
        processed_stop_ids = StopAttraction.objects.values_list('stop_id', flat=True).distinct()
        stops_to_process = Stop.objects.exclude(stop_id__in=processed_stop_ids)
        
        total_stops = stops_to_process.count()
        if total_stops == 0:
            self.stdout.write(self.style.SUCCESS("All stops already have attractions assigned!"))
            return

        self.stdout.write(self.style.SUCCESS(f"Starting work on 4 workers. Remaining: {total_stops} stops."))

        # Load stops into a thread-safe in-memory queue
        job_queue = queue.Queue()
        for stop in stops_to_process:
            job_queue.put(stop)

        # Initialize the progress bar
        pbar = tqdm(total=total_stops, desc="Seeding attractions", unit="stop")

        # Worker function (executed independently by each thread)
        def worker(mirror_url, worker_name):
            while not job_queue.empty():
                try:
                    stop = job_queue.get_nowait()
                except queue.Empty:
                    break

                elements = self.fetch_osm_data(stop.stop_lat, stop.stop_lon, mirror_url)
                
                if elements is None:
                    error_msg = f"[{worker_name}: {mirror_url[-20:]}] exceeded {stop.stop_name} number of retries. Skipping this stop for now."
                    logger.error(error_msg)

                if elements and len(elements) > 0:
                    self.save_to_db(stop, elements)
                    logger.info(f"[{worker_name}: {mirror_url[-20:]}] Saved {len(elements)} attractions for: {stop.stop_name}")
                else:
                    logger.info(f"[{worker_name}: {mirror_url[-20:]}] No attractions found for: {stop.stop_name}")
                
                # Mark task as done and update the progress bar by 1
                job_queue.task_done()
                pbar.update(1)
                
                # Worker rests before taking the next stop
                time.sleep(1.5)

        # Start threads
        threads = []
        for i, mirror in enumerate(OVERPASS_MIRRORS):
            worker_name = f"Worker-{i+1}"
            t = threading.Thread(target=worker, args=(mirror, worker_name))
            t.start()
            threads.append(t)

        # Wait for all threads to finish their work
        for t in threads:
            t.join()

        pbar.close()
        self.stdout.write(self.style.SUCCESS('MULTI-THREADED SEEDING COMPLETED SUCCESSFULLY!'))


    def fetch_osm_data(self, lat, lon, mirror_url, radius=5000, max_retries=3):
        """Worker uses only its assigned mirror_url"""
        query = f"""
        [out:json][timeout:25];
        (
          node["tourism"~"museum|attraction|viewpoint|gallery"](around:{radius},{lat},{lon});
          way["tourism"~"museum|attraction|viewpoint|gallery"](around:{radius},{lat},{lon});
          node["historic"~"castle|monument|ruins"](around:{radius},{lat},{lon});
          way["historic"~"castle|monument|ruins"](around:{radius},{lat},{lon});
        );
        out center;
        """
        
        for attempt in range(max_retries):
            try:
                response = requests.post(mirror_url, data={'data': query}, timeout=30)
                if response.status_code == 429:
                    time.sleep(10 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.json().get('elements', [])
            except Exception:
                time.sleep(5)
        return []

    def save_to_db(self, stop, elements):
        """Saves data to Supabase. Protected against thread collisions."""
        for el in elements:
            tags = el.get('tags', {})
            name = tags.get('name')
            if not name:
                continue
                
            osm_id = str(el.get('id'))
            category = tags.get('tourism') or tags.get('historic') or 'Other'
            p_lat = el.get('lat') or el.get('center', {}).get('lat')
            p_lon = el.get('lon') or el.get('center', {}).get('lon')

            if p_lat is None or p_lon is None:
                continue

            dist = get_distance(stop.stop_lat, stop.stop_lon, p_lat, p_lon)

            # Protection in case 2 Workers try to create the same attraction at the exact same time
            try:
                with transaction.atomic():
                    attraction_obj, _ = Attraction.objects.get_or_create(
                        attraction_id=osm_id,
                        defaults={
                            'attraction_name': name[:250],
                            'attraction_category': category[:90],
                            'attraction_lat': p_lat,
                            'attraction_lon': p_lon
                        }
                    )
            except IntegrityError:
                attraction_obj = Attraction.objects.get(attraction_id=osm_id)

            StopAttraction.objects.update_or_create(
                stop=stop,
                attraction=attraction_obj,
                defaults={'distance_meters': int(dist)}
            )