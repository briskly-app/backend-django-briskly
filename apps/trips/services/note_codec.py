import json

NOTE_PREFIX = '<!--briskly-note:v1-->'


def decode_note_html(html_source: str) -> dict | None:
    if not html_source or not html_source.startswith(NOTE_PREFIX):
        return None
    try:
        return json.loads(html_source[len(NOTE_PREFIX):])
    except json.JSONDecodeError:
        return None
