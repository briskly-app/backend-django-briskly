import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create/update a local test user (default: testuser) with a known password."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="testuser",
            help="Username to create/update (default: testuser).",
        )
        parser.add_argument(
            "--password",
            default=None,
            help="Password to set. If omitted, uses TESTUSER_PASSWORD env var.",
        )
        parser.add_argument(
            "--email",
            default="testuser@example.com",
            help="Email to set if user is created (default: testuser@example.com).",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"] or os.environ.get("TESTUSER_PASSWORD")
        email = options["email"]

        if not password:
            self.stderr.write(
                "Missing password. Provide --password or set TESTUSER_PASSWORD env var."
            )
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )

        user.set_password(password)
        if created and not user.email:
            user.email = email
        user.save(update_fields=["password", "email"])

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} user '{username}' with a usable password."
            )
        )

