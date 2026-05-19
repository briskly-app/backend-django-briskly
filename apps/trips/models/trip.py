import uuid

from django.db import models


class UserTrip(models.Model):
    slug = models.CharField(max_length=255, unique=True, blank=True)
    name = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'routes_usertrip'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuid.uuid4().hex[:8]

        if not self.name:
            self.name = f"Empty_{self.slug}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
