import time
import logging
import requests
from tqdm import tqdm
from django.core.management.base import BaseCommand
from routes.models import City

logger = logging.getLogger('seed_descriptions_for_cities')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('seed_descriptions_for_cities.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

WIKIPEDIA_TIMEOUT = 1.2
HTTP_TIMEOUT = 15
MAX_PARAGRAPHS = 3
MAX_RETRIES = 3
USER_AGENT = 'BrisklyTransitApp/1.0 (descriptions seeder; example@example.com)'


class Command(BaseCommand):
    help = (
        'Fetches a short description (first few paragraphs) from Wikipedia for each '
        'city and stores it in City.city_description. Paragraphs are separated by '
        'a single newline character (\\n).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing descriptions (by default cities with a description are skipped).',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of processed cities (useful for testing).',
        )
        parser.add_argument(
            '--sleep',
            type=float,
            default=WIKIPEDIA_TIMEOUT,
            help=f'Pause [s] between Wikipedia requests (default {WIKIPEDIA_TIMEOUT}s).',
        )
        parser.add_argument(
            '--max-paragraphs',
            type=int,
            default=MAX_PARAGRAPHS,
            help=f'Maximum number of paragraphs per city (default {MAX_PARAGRAPHS}).',
        )

    def fetch_wikipedia_extract(self, city_name, language='en'):
        url = f'https://{language}.wikipedia.org/w/api.php'

        params = {
            'action': 'query',
            'prop': 'extracts',
            'exintro': 1,
            'explaintext': 1,
            'redirects': 1,
            'titles': city_name,
            'format': 'json',
            'formatversion': 2,
        }
        headers = {'User-Agent': USER_AGENT}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=HTTP_TIMEOUT,
                )
            except requests.exceptions.Timeout:
                logger.warning(
                    f"Timeout while fetching description for '{city_name}' "
                    f"({language}.wikipedia, attempt {attempt}/{MAX_RETRIES})"
                )
                time.sleep(2 * attempt)
                continue
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Network error for '{city_name}' ({language}.wikipedia, "
                    f"attempt {attempt}/{MAX_RETRIES}): {e}"
                )
                time.sleep(2 * attempt)
                continue

            if response.status_code == 429:
                wait = 10 * attempt
                logger.warning(
                    f"HTTP 429 (rate limit) for '{city_name}' - waiting {wait}s "
                    f"(attempt {attempt}/{MAX_RETRIES})"
                )
                time.sleep(wait)
                continue

            if response.status_code != 200:
                logger.warning(
                    f"HTTP {response.status_code} for '{city_name}' ({language}.wikipedia)"
                )
                return None

            try:
                data = response.json()
            except ValueError:
                logger.error(f"Invalid JSON for '{city_name}' ({language}.wikipedia)")
                return None

            pages = data.get('query', {}).get('pages', [])
            if not pages:
                return None

            page = pages[0]
            if page.get('missing'):
                return None

            extract = page.get('extract')
            if not extract or not extract.strip():
                return None

            return extract

        return None

    def extract_to_paragraphs(self, extract, max_paragraphs):
        if not extract:
            return []

        raw_paragraphs = [p.strip() for p in extract.split('\n')]
        paragraphs = [p for p in raw_paragraphs if p]

        cleaned = []
        for p in paragraphs:
            if p.endswith(':') and len(p) < 80:
                continue
            cleaned.append(p)
            if len(cleaned) >= max_paragraphs:
                break

        return cleaned

    def build_description(self, city, max_paragraphs):
        extract = self.fetch_wikipedia_extract(city.city_name, language='en')

        if not extract and city.city_country_code:
            lang = city.city_country_code.lower()
            if lang and lang != 'en':
                logger.info(
                    f"No EN result for '{city.city_name}', trying {lang}.wikipedia"
                )
                extract = self.fetch_wikipedia_extract(city.city_name, language=lang)

        if not extract:
            return None

        paragraphs = self.extract_to_paragraphs(extract, max_paragraphs)
        if not paragraphs:
            return None

        return '\n'.join(paragraphs)

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']
        sleep_seconds = options['sleep']
        max_paragraphs = options['max_paragraphs']

        qs = City.objects.all().order_by('city_id')
        if not force:
            qs = qs.filter(city_description__isnull=True) | qs.filter(city_description='')
            qs = qs.distinct()

        total = qs.count()
        if limit is not None:
            qs = qs[:limit]
            total = min(total, limit)

        logger.info(
            f"Start: {total} cities to process "
            f"(force={force}, sleep={sleep_seconds}s, max_paragraphs={max_paragraphs})"
        )

        if total == 0:
            logger.info("No cities to process.")
            self.stdout.write(self.style.SUCCESS("No cities to process."))
            return

        success = 0
        skipped = 0
        failed = 0

        pbar = tqdm(qs.iterator(), total=total, desc="Wikipedia descriptions", unit="city")
        for city in pbar:
            pbar.set_postfix_str(city.city_name[:30])

            try:
                description = self.build_description(city, max_paragraphs)
            except Exception as e:
                logger.exception(f"Unexpected error for '{city.city_name}': {e}")
                failed += 1
                time.sleep(sleep_seconds)
                continue

            if not description:
                logger.warning(
                    f"No Wikipedia description found for '{city.city_name}' "
                    f"(id={city.city_id})"
                )
                skipped += 1
            else:
                City.objects.filter(pk=city.pk).update(city_description=description)
                paragraph_count = description.count('\n') + 1
                logger.info(
                    f"Saved description for '{city.city_name}' "
                    f"(id={city.city_id}, paragraphs={paragraph_count}, "
                    f"chars={len(description)})"
                )
                success += 1

            time.sleep(sleep_seconds)

        pbar.close()

        summary = (
            f"Finished. OK: {success}, no description: {skipped}, errors: {failed}, "
            f"total: {total}"
        )
        logger.info(summary)
        self.stdout.write(self.style.SUCCESS(summary))
