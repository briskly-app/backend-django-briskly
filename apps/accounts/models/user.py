from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    avatar_url = models.URLField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return self.email or self.username
