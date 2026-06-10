from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import requests
from django.utils import timezone
from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from apps.logistics.models import City
from apps.logistics.services.attractiveness import city_description_paragraphs
from apps.trips.models import UserTrip, UserTripConnectionNote
from apps.trips.services.note_codec import decode_note_html

FONTS_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
FONT_REGULAR = 'DejaVuSans'
FONT_BOLD = 'DejaVuSans-Bold'

MONTHS_PL = (
    '',
    'stycznia',
    'lutego',
    'marca',
    'kwietnia',
    'maja',
    'czerwca',
    'lipca',
    'sierpnia',
    'września',
    'października',
    'listopada',
    'grudnia',
)

PAGE_WIDTH, PAGE_HEIGHT = A4
CONTENT_WIDTH = PAGE_WIDTH - 4 * cm


@dataclass
class JournalStop:
    stop_id: str
    title: str
    city_name: str
    stay_range_label: str
    arrival_label: str
    departure_label: str
    city_image_url: str
    city_description: str
    notes: list[dict] = field(default_factory=list)


def build_journal_pdf_filename(trip_name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', '', trip_name or '').strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if not cleaned:
        cleaned = 'Podróż'
    return f'Briskly - {cleaned}.pdf'


def _register_fonts() -> None:
    regular = FONTS_DIR / 'DejaVuSans.ttf'
    bold = FONTS_DIR / 'DejaVuSans-Bold.ttf'
    if regular.exists():
        pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular)))
    if bold.exists():
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold)))


def _escape(text: str) -> str:
    return (
        text.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('\n', '<br/>')
    )


def _format_pl_date(value: date | datetime | str | None) -> str:
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return value
    if isinstance(value, datetime):
        value = value.date()
    return f'{value.day} {MONTHS_PL[value.month]} {value.year}'


def _format_time(value) -> str:
    if not value:
        return ''
    return str(value)[:5]


def _format_arrival_departure_line(kind: str, day, time) -> str:
    parts = []
    if time:
        parts.append(_format_time(time))
    if day:
        parts.append(_format_pl_date(day))
    if not parts:
        return ''
    return f'{kind}: {" ".join(parts)}'


def _format_stay_range(arrival_day, departure_day) -> str:
    if not arrival_day and not departure_day:
        return ''
    if arrival_day and departure_day:
        if arrival_day == departure_day:
            return _format_pl_date(arrival_day)
        if (
            arrival_day.year == departure_day.year
            and arrival_day.month == departure_day.month
        ):
            return (
                f'{arrival_day.day}–{departure_day.day} '
                f'{MONTHS_PL[arrival_day.month]} {arrival_day.year}'
            )
        return f'{_format_pl_date(arrival_day)} – {_format_pl_date(departure_day)}'
    if arrival_day:
        return f'od {_format_pl_date(arrival_day)}'
    return f'do {_format_pl_date(departure_day)}'


def _city_for_stop(stop) -> City | None:
    if not stop or not stop.place:
        return None
    return stop.place.place_city


def _city_description_text(city: City | None, max_paragraphs: int = 3) -> str:
    if not city:
        return ''
    paragraphs = city_description_paragraphs(city)[:max_paragraphs]
    return '\n\n'.join(paragraphs)


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name='TitlePageBrand',
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#0ea5e9'),
            spaceAfter=24,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='TitlePageName',
            fontName=FONT_BOLD,
            fontSize=28,
            leading=34,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=16,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='TitlePageMeta',
            fontName=FONT_REGULAR,
            fontSize=12,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#475569'),
            spaceAfter=8,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='StopHeading',
            fontName=FONT_BOLD,
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='StayRange',
            fontName=FONT_BOLD,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='StopMeta',
            fontName=FONT_REGULAR,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=4,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='CityDescription',
            fontName=FONT_REGULAR,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor('#475569'),
            spaceAfter=16,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='NotesSectionHeading',
            fontName=FONT_BOLD,
            fontSize=13,
            leading=17,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=8,
            spaceAfter=10,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='NoteTitle',
            fontName=FONT_BOLD,
            fontSize=13,
            leading=17,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=4,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='NoteMeta',
            fontName=FONT_REGULAR,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=6,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='NoteBody',
            fontName=FONT_REGULAR,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#334155'),
            spaceAfter=14,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='Caption',
            fontName=FONT_REGULAR,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#94a3b8'),
            spaceAfter=12,
        ),
    )
    return styles


def _note_to_entry(note: UserTripConnectionNote, connection) -> dict:
    decoded = decode_note_html(note.html_source)
    default_stop_id = f'stop-{connection.destination_stop.stop_id}'

    if note.image_url:
        return {
            'kind': 'image',
            'stop_id': decoded.get('scheduleStopId') if decoded else default_stop_id,
            'title': decoded.get('title') if decoded else 'Zdjęcie',
            'day': decoded.get('day') if decoded else str(connection.arrival_date),
            'time': decoded.get('time') if decoded else _format_time(connection.arrival_time),
            'body': '',
            'image_url': note.image_url,
            'sort_order': note.sequence_id,
        }

    return {
        'kind': 'text',
        'stop_id': decoded.get('scheduleStopId') if decoded else default_stop_id,
        'title': decoded.get('title') if decoded else 'Notatka',
        'day': decoded.get('day') if decoded else str(connection.arrival_date),
        'time': decoded.get('time') if decoded else _format_time(connection.arrival_time),
        'body': decoded.get('body') if decoded else note.html_source,
        'image_url': '',
        'sort_order': note.sequence_id,
    }


def _build_journal_stop(
    stop,
    *,
    arrival_day=None,
    arrival_time=None,
    departure_day=None,
    departure_time=None,
) -> JournalStop:
    city = _city_for_stop(stop)
    city_name = city.city_name if city else ''
    stop_name = stop.stop_name if stop else ''
    display_name = city_name or stop_name

    stay_range = ''
    if arrival_day and departure_day:
        stay_range = _format_stay_range(arrival_day, departure_day)

    return JournalStop(
        stop_id=f'stop-{stop.stop_id}',
        title=stop_name,
        city_name=display_name,
        stay_range_label=stay_range,
        arrival_label=_format_arrival_departure_line('Przyjazd', arrival_day, arrival_time),
        departure_label=_format_arrival_departure_line('Wyjazd', departure_day, departure_time),
        city_image_url=city.city_thumbnail_url if city and city.city_thumbnail_url else '',
        city_description=_city_description_text(city),
    )


def _collect_journal_stops(trip: UserTrip) -> list[JournalStop]:
    connections = list(
        trip.connections.select_related(
            'starting_stop__place__place_city',
            'destination_stop__place__place_city',
        )
        .prefetch_related('notes')
        .order_by('id'),
    )

    if not connections:
        return []

    arrivals: dict[str, tuple] = {}
    departures: dict[str, tuple] = {}
    ordered_stop_ids: list[str] = []
    stops_by_id: dict[str, object] = {}

    for connection in connections:
        starting = connection.starting_stop
        if starting:
            start_key = starting.stop_id
            if start_key not in stops_by_id:
                ordered_stop_ids.append(start_key)
                stops_by_id[start_key] = starting
            departures[start_key] = (connection.departure_date, connection.departure_time)

        destination = connection.destination_stop
        if not destination:
            continue

        dest_key = destination.stop_id
        if dest_key not in stops_by_id:
            ordered_stop_ids.append(dest_key)
            stops_by_id[dest_key] = destination

        arrivals[dest_key] = (connection.arrival_date, connection.arrival_time)

    notes_by_stop: dict[str, list[dict]] = {}
    for connection in connections:
        for note in connection.notes.all():
            entry = _note_to_entry(note, connection)
            notes_by_stop.setdefault(entry['stop_id'], []).append(entry)

    stops: list[JournalStop] = []
    for stop_key in ordered_stop_ids:
        stop = stops_by_id[stop_key]
        arrival = arrivals.get(stop_key)
        departure = departures.get(stop_key)
        journal_stop = _build_journal_stop(
            stop,
            arrival_day=arrival[0] if arrival else None,
            arrival_time=arrival[1] if arrival else None,
            departure_day=departure[0] if departure else None,
            departure_time=departure[1] if departure else None,
        )
        journal_stop.notes = sorted(
            notes_by_stop.get(journal_stop.stop_id, []),
            key=lambda item: item['sort_order'],
        )
        stops.append(journal_stop)

    return stops


def _load_image_flowable(image_url: str, max_width: float, max_height: float):
    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        pil_image = PilImage.open(io.BytesIO(response.content))
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')

        width, height = pil_image.size
        scale = min(max_width / width, max_height / height, 1.0)
        draw_width = width * scale
        draw_height = height * scale

        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        return Image(buffer, width=draw_width, height=draw_height)
    except Exception:
        return None


def _build_title_page(trip: UserTrip, styles, location: str) -> list:
    story = [Spacer(1, 4.5 * cm)]

    story.append(Paragraph('Briskly', styles['TitlePageBrand']))
    story.append(Paragraph('Dziennik podróży', styles['TitlePageMeta']))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(_escape(trip.name or 'Podróż'), styles['TitlePageName']))

    if trip.description:
        story.append(Paragraph(_escape(trip.description), styles['TitlePageMeta']))

    if location:
        story.append(Paragraph(_escape(location), styles['TitlePageMeta']))

    date_range = _format_pl_date(trip.start_date or trip.created_at.date())
    if trip.end_date:
        date_range = f'{date_range} – {_format_pl_date(trip.end_date)}'
    story.append(Paragraph(date_range, styles['TitlePageMeta']))

    status = 'Zakończona' if trip.end_date else 'W trakcie'
    story.append(Paragraph(status, styles['TitlePageMeta']))
    story.append(Spacer(1, 1.5 * cm))
    story.append(
        Paragraph(
            f'Wygenerowano {timezone.localtime().strftime("%d.%m.%Y %H:%M")}',
            styles['TitlePageMeta'],
        ),
    )
    story.append(PageBreak())
    return story


def _build_stop_section(stop: JournalStop, styles) -> list:
    story = [Paragraph(_escape(stop.city_name), styles['StopHeading'])]

    if stop.stay_range_label:
        story.append(Paragraph(_escape(stop.stay_range_label), styles['StayRange']))

    schedule_lines = [
        line for line in [stop.arrival_label, stop.departure_label] if line
    ]
    for line in schedule_lines:
        story.append(Paragraph(_escape(line), styles['StopMeta']))

    if stop.title and stop.title != stop.city_name:
        story.append(
            Paragraph(_escape(f'Przystanek: {stop.title}'), styles['StopMeta']),
        )

    story.append(Spacer(1, 0.3 * cm))

    if stop.city_image_url:
        image = _load_image_flowable(stop.city_image_url, CONTENT_WIDTH, 8 * cm)
        if image:
            story.append(image)
            story.append(Spacer(1, 0.4 * cm))

    if stop.city_description:
        story.append(Paragraph(_escape(stop.city_description), styles['CityDescription']))

    if not stop.notes:
        story.append(Spacer(1, 0.6 * cm))
        return story

    story.append(Paragraph('Notatki', styles['NotesSectionHeading']))

    for note in stop.notes:
        meta_parts = [
            _format_pl_date(note['day']) if note['day'] else '',
            note['time'],
        ]
        meta = ' • '.join(part for part in meta_parts if part)

        if note['kind'] == 'image':
            story.append(Paragraph(_escape(note['title']), styles['NoteTitle']))
            if meta:
                story.append(Paragraph(_escape(meta), styles['NoteMeta']))
            image = _load_image_flowable(note['image_url'], CONTENT_WIDTH, 10 * cm)
            if image:
                story.append(image)
            else:
                story.append(
                    Paragraph('Nie udało się wczytać zdjęcia.', styles['Caption']),
                )
            story.append(Spacer(1, 0.4 * cm))
            continue

        story.append(Paragraph(_escape(note['title']), styles['NoteTitle']))
        if meta:
            story.append(Paragraph(_escape(meta), styles['NoteMeta']))
        if note['body']:
            story.append(Paragraph(_escape(note['body']), styles['NoteBody']))

    story.append(Spacer(1, 0.6 * cm))
    return story


def build_journal_pdf(trip: UserTrip) -> bytes:
    _register_fonts()
    styles = _build_styles()
    stops = _collect_journal_stops(trip)
    location = stops[-1].city_name if stops else ''

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f'Dziennik — {trip.name}',
        author='Briskly',
    )

    story = _build_title_page(trip, styles, location)

    if not stops:
        story.append(
            Paragraph(
                'Ta podróż nie ma jeszcze zaplanowanych przystanków.',
                styles['NoteBody'],
            ),
        )
    else:
        for index, stop in enumerate(stops, start=1):
            if index > 1:
                story.append(PageBreak())
            story.extend(_build_stop_section(stop, styles))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
