from django.db import models

from apps.trips.models.segment import UserTripConnection


class UserTripConnectionNote(models.Model):
    user_trip_connection = models.ForeignKey(
        UserTripConnection,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    sequence_id = models.PositiveIntegerField()
    html_source = models.TextField(blank=True, default='')
    image_url = models.URLField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'routes_usertripconnectionnote'
        ordering = ['sequence_id', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['user_trip_connection', 'sequence_id'],
                name='unique_note_sequence_per_connection',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(html_source__gt='', image_url='')
                    | models.Q(html_source='', image_url__gt='')
                ),
                name='note_exactly_one_content_type',
            ),
        ]

    def __str__(self):
        return f'Note {self.pk} (seq={self.sequence_id}) on connection {self.user_trip_connection_id}'

    @property
    def is_image_note(self):
        return bool(self.image_url)
