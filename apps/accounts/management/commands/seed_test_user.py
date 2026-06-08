import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create/update a local test user with email-based login."

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            default='testuser@example.com',
            help='E-mail (also used as username). Default: testuser@example.com',
        )
        parser.add_argument(
            '--password',
            default=None,
            help='Password to set. If omitted, uses TESTUSER_PASSWORD env var.',
        )
        parser.add_argument(
            '--display-name',
            default='Test User',
            help='First/last name seed (default: Test User).',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        password = options['password'] or os.environ.get('TESTUSER_PASSWORD')
        display_name = options['display_name'].strip()
        parts = display_name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        if not password:
            self.stderr.write(
                'Missing password. Provide --password or set TESTUSER_PASSWORD env var.',
            )
            return

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.filter(username__iexact='testuser').first()

        created = user is None
        if created:
            user = User(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
        else:
            user.username = email
            user.email = email
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        user.set_password(password)
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} user '{email}' — log in with this e-mail.",
            ),
        )
