from django.db import transaction
from django.db.models import Max

from apps.trips.models import UserTripConnection, UserTripConnectionNote


def next_sequence_id(connection: UserTripConnection) -> int:
    current_max = connection.notes.aggregate(Max('sequence_id'))['sequence_id__max']
    return (current_max or 0) + 1


@transaction.atomic
def reorder_connection_notes(connection: UserTripConnection, sequence_map: dict[int, int]) -> None:
    if not sequence_map:
        return

    if len(set(sequence_map.values())) != len(sequence_map):
        raise ValueError('sequence_id values must be unique within the reorder payload.')

    note_ids = list(sequence_map.keys())
    notes = list(
        UserTripConnectionNote.objects.select_for_update().filter(
            user_trip_connection=connection,
            pk__in=note_ids,
        ),
    )

    if len(notes) != len(note_ids):
        raise ValueError('One or more note ids do not belong to this connection.')

    offset = 1_000_000
    for note in notes:
        note.sequence_id = note.pk + offset
    UserTripConnectionNote.objects.bulk_update(notes, ['sequence_id'])

    for note in notes:
        note.sequence_id = sequence_map[note.pk]
    UserTripConnectionNote.objects.bulk_update(notes, ['sequence_id'])
