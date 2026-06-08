from __future__ import annotations

import io
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
    subtitle: str
    date_label: str
    time_label: str
    notes: list[dict] = field(default_factory=list)


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


def _build_styles():
    styles = getSampleStyleSheet()
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
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4,
        ),
    )
    styles.add(
        ParagraphStyle(
            name='StopMeta',
            fontName=FONT_REGULAR,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=12,
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


def _collect_journal_stops(trip: UserTrip) -> list[JournalStop]:
    connections = (
        trip.connections.select_related(
            'starting_stop__place__place_city',
            'destination_stop__place__place_city',
        )
        .prefetch_related('notes')
        .order_by('id')
    )

    if not connections:
        return []

    stops: list[JournalStop] = []
    notes_by_stop: dict[str, list[dict]] = {}

    first = connections[0]
    starting = first.starting_stop
    starting_city = starting.place.place_city if starting.place else None
    stops.append(
        JournalStop(
            stop_id=f'stop-{starting.stop_id}',
            title=starting.stop_name,
            subtitle=starting_city.city_name if starting_city else '',
            date_label=_format_pl_date(first.departure_date),
            time_label=_format_time(first.departure_time),
        ),
    )

    for connection in connections:
        destination = connection.destination_stop
        dest_city = destination.place.place_city if destination.place else None
        stop_id = f'stop-{destination.stop_id}'
        stops.append(
            JournalStop(
                stop_id=stop_id,
                title=destination.stop_name,
                subtitle=dest_city.city_name if dest_city else '',
                date_label=_format_pl_date(connection.arrival_date),
                time_label=_format_time(connection.arrival_time),
            ),
        )

        for note in connection.notes.all():
            entry = _note_to_entry(note, connection)
            notes_by_stop.setdefault(entry['stop_id'], []).append(entry)

    for stop in stops:
        stop.notes = sorted(
            notes_by_stop.get(stop.stop_id, []),
            key=lambda item: item['sort_order'],
        )

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
    story = [Spacer(1, 5 * cm)]

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


def _build_stop_section(stop: JournalStop, index: int, styles) -> list:
    story = [
        Paragraph(f'Przystanek {index}: {_escape(stop.title)}', styles['StopHeading']),
        Paragraph(
            _escape(
                ' • '.join(
                    part
                    for part in [stop.subtitle, stop.date_label, stop.time_label]
                    if part
                ),
            ),
            styles['StopMeta'],
        ),
    ]

    if not stop.notes:
        story.append(Paragraph('Brak notatek dla tego przystanku.', styles['NoteBody']))
        story.append(Spacer(1, 0.5 * cm))
        return story

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
    location = stops[-1].subtitle if stops else ''

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
            story.extend(_build_stop_section(stop, index, styles))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
