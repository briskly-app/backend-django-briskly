import time
import supabase
import queue
import requests
import threading
from tqdm import tqdm
import logging
import unicodedata
import os
from dotenv import load_dotenv
from django.core.management.base import BaseCommand
from routes.models import City

load_dotenv()
supabase = supabase.create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))

BOUNDARY_CITY_POPULATION = 20000
TEMP_DIRECTORY = 'temp_images'
WIKIPEDIA_TIMEOUT = 3
UNSPLASH_TIMEOUT = 1
UNSPLASH_HOUR_LIMIT = 50

logger = logging.getLogger('search_and_upload_images_for_cities')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('search_and_upload_images_for_cities.log', encoding='utf-8')
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
    help = 'Search and upload images for cities using the Unsplash API and Wikipedia API'

    def search_unsplash_image(self, city_name):
        url = "https://api.unsplash.com/search/photos"
    
        params = {
            'query': f"{city_name} famous landmark architecture viewpoint",
            'client_id': os.getenv('UNSPLASH_CLIENT_ID'),
            'per_page': 1,
            'orientation': 'landscape',
            'order_by': 'popular'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    logger.info(f"Unsplash API returned an image for {city_name}")
                    return data['results'][0]['urls']['regular']
                    
            logger.warning(f"Unsplash API did not return a valid image for {city_name} (HTTP {response.status_code})")
            return None
            
        except Exception as e:
            logger.error(f"Error while searching Unsplash for {city_name}: {e}")
            return None
        
    def search_wikipedia_image(self, city_name, language='en'):
        urlEnglish = "https://en.wikipedia.org/w/api.php"
        url = f"https://{language}.wikipedia.org/w/api.php"
    
        params = {
            'action': 'query',
            'titles': city_name,
            'prop': 'pageimages',
            'format': 'json',
            'pithumbsize': 800
        }
        
        headers = {
            'User-Agent': 'BrisklyTransitApp/1.0 (example@example.com)'
        }
        
        try:
            response = requests.get(urlEnglish, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})
                
                for page_id, page_info in pages.items():
                    if 'thumbnail' in page_info:
                        logger.info(f"Wikipedia API returned an image for {city_name} from page ID {page_id}")
                        return page_info['thumbnail']['source']
                        
            logger.warning(f"Wikipedia API did not return a valid image for {city_name} (HTTP {response.status_code}) - en version")

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})
                
                for page_id, page_info in pages.items():
                    if 'thumbnail' in page_info:
                        logger.info(f"Wikipedia API returned an image for {city_name} from page ID {page_id}")
                        return page_info['thumbnail']['source']
                    
            logger.warning(f"Wikipedia API did not return a valid image for {city_name} (HTTP {response.status_code}) - {language} version")
            return None
            
        except Exception as e:
            logger.error(f"Error while searching Wikipedia for {city_name}: {e}")
            return None
        
    def download_image_locally(self, url, city_id):
        if not os.path.exists(TEMP_DIRECTORY):
            os.makedirs(TEMP_DIRECTORY)

        filepath = os.path.join(TEMP_DIRECTORY, city_id + '.jpg')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,pl;q=0.8',
            'Referer': 'https://wikipedia.org/'
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, stream=True, timeout=10)
                
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    logger.info(f"Successfully downloaded image for {city_id} to {filepath}")
                    return filepath
                else:
                    logger.warning(f"HTTP {response.status_code} for {city_id} with URL: {url} (Attempt {attempt + 1}/{max_retries})")
                    wait_time = (attempt + 1) * 5
                    time.sleep(wait_time)
                    continue
                    
            except Exception as e:
                logger.error(f"Error while downloading image for {city_id}: {e} (Attempt {attempt + 1}/{max_retries})")
                return None
        
    def upload_image_to_supabase_bucket(self, filepath, city_id, bucket_name='city_images'):
        if not filepath or not os.path.exists(filepath):
            logger.error(f"File {filepath} does not exist. Cannot upload to Supabase.")
            return None

        original_filename = os.path.basename(filepath)
        name_without_ext = original_filename.replace('.jpg', '')

        safe_name = normalize_to_ascii(name_without_ext)
        safe_name = "".join(c if c.isalnum() else '_' for c in safe_name)

        safe_filename = f"{safe_name}.jpg"

        try:
            with open(filepath, 'rb') as f:
                supabase.storage.from_(bucket_name).upload(
                    path=safe_filename, 
                    file=f, 
                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                )
                
            public_url = supabase.storage.from_(bucket_name).get_public_url(safe_filename)
            logger.info(f"Successfully uploaded image for {city_id} to Supabase bucket '{bucket_name}'. Public URL: {public_url}")
            
            os.remove(filepath)
            logger.info(f"Cleaned up local file {filepath} after upload for {city_id}")

            return public_url

        except Exception as e:
            logger.error(f"Error while uploading image for {city_id} to Supabase: {e}")
            return None

    def update_city_thumbnail(self, city_id, thumbnail_url):
        try:
            City.objects.filter(city_id=city_id).update(city_thumbnail_url=thumbnail_url)
            logger.info(f"Updated city {city_id} with URL: {thumbnail_url}")

        except Exception as e:
            logger.error(f"Error while updating city {city_id} with thumbnail URL: {e}")

    def process_city_unsplash(self, city):
        thumbnail_url = self.search_unsplash_image(city.city_name)
        if thumbnail_url:
            return self.download_image_locally(thumbnail_url, city.city_id)
        else:
            logger.info(f"No image found on Unsplash for {city.city_name}. Falling back to Wikipedia.")
            return self.process_city_wikipedia(city)
        
    def process_city_wikipedia(self, city):
        thumbnail_url = self.search_wikipedia_image(city.city_name, city.city_country_code.lower())
        time.sleep(WIKIPEDIA_TIMEOUT)
        if thumbnail_url:
            return self.download_image_locally(thumbnail_url, city.city_id)

    def worker_wikipedia(self, cities):
        for city in cities:
            local_filepath = self.process_city_wikipedia(city)
            if local_filepath:
                self.files_to_upload.put((city.city_id, local_filepath))
            else:
                self.pbar.update(1)
            time.sleep(WIKIPEDIA_TIMEOUT)

    def worker_unsplash(self, cities):
        current_unsplash_requests = 0
        for city in cities:
            if current_unsplash_requests >= UNSPLASH_HOUR_LIMIT:
                # logger.warning("Reached Unsplash hourly request limit. Waiting...")
                # time.sleep(3600)  # Wait for an hour
                # current_unsplash_requests = 0
                logger.warning("Reached Unsplash hourly request limit. Skipping remaining cities for Unsplash.")
                break

            local_filepath = self.process_city_unsplash(city)
            if local_filepath:
                self.files_to_upload.put((city.city_id, local_filepath))
            else:
                self.pbar.update(1)
            time.sleep(UNSPLASH_TIMEOUT)

    def worker_upload_and_save(self):
        while True:
            item = self.files_to_upload.get()
            if item is None:
                break
            
            city_id, local_filepath = item
            public_url = self.upload_image_to_supabase_bucket(local_filepath, city_id)
            
            if public_url:
                self.update_city_thumbnail(city_id, public_url)
                
            self.pbar.update(1)
            self.files_to_upload.task_done()


    def handle(self, *args, **kwargs):
        
        large_cities = list(City.objects.filter(city_population__gt=BOUNDARY_CITY_POPULATION, city_thumbnail_url__isnull=True))
        small_cities = list(City.objects.filter(city_population__lte=BOUNDARY_CITY_POPULATION, city_thumbnail_url__isnull=True))

        total_cities = len(large_cities) + len(small_cities)
        logger.info(f"Processing: {len(large_cities)} large and {len(small_cities)} small cities.")

        if total_cities == 0:
            logger.info("All cities already have thumbnails")
            return

        self.pbar = tqdm(total=total_cities, desc="Processing cities", unit="city")
        self.files_to_upload = queue.Queue()

        t_wiki = threading.Thread(target=self.worker_wikipedia, args=(small_cities,))
        t_unsplash = threading.Thread(target=self.worker_unsplash, args=(large_cities,))
        t_upload = threading.Thread(target=self.worker_upload_and_save)

        t_wiki.start()
        t_unsplash.start()
        t_upload.start()

        t_wiki.join()
        t_unsplash.join()

        # for file in os.listdir(TEMP_DIRECTORY):
        #     if file.endswith('.jpg'):
        #         city_id = os.path.splitext(file)[0]
        #         local_filepath = os.path.join(TEMP_DIRECTORY, file)
        #         self.files_to_upload.put((city_id, local_filepath))
        
        self.files_to_upload.put(None)
        
        t_upload.join()

        self.pbar.close()
        logger.info("All cities processed successfully!")




