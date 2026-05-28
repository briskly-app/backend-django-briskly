import os

from django.core.management.base import BaseCommand
from django.db import transaction

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = "Create/Update django.contrib.sites.Site and allauth SocialApp entries from environment variables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            default=os.environ.get("SITE_DOMAIN", "localhost:8000"),
            help="Domain for django_site (default: SITE_DOMAIN env or localhost:8000).",
        )
        parser.add_argument(
            "--name",
            default=os.environ.get("SITE_NAME", "Briskly"),
            help="Name for django_site (default: SITE_NAME env or Briskly).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        domain = options["domain"]
        name = options["name"]

        site, _ = Site.objects.update_or_create(
            id=1,
            defaults={"domain": domain, "name": name},
        )

        created = []
        updated = []
        skipped = []

        def upsert(provider, env_id, env_secret):
            client_id = os.environ.get(env_id)
            secret = os.environ.get(env_secret)

            if not client_id or not secret:
                skipped.append(provider)
                return

            app, was_created = SocialApp.objects.update_or_create(
                provider=provider,
                defaults={
                    "name": provider,
                    "client_id": client_id,
                    "secret": secret,
                },
            )
            app.sites.add(site)

            (created if was_created else updated).append(provider)

        upsert("google", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")
        upsert("github", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET")

        self.stdout.write(self.style.SUCCESS(f"Site set to: {site.domain} (id=1)"))
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created SocialApp: {', '.join(created)}"))
        if updated:
            self.stdout.write(self.style.SUCCESS(f"Updated SocialApp: {', '.join(updated)}"))
        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped (missing env vars): "
                    + ", ".join(
                        f"{p} (set {p.upper()}_CLIENT_ID and {p.upper()}_CLIENT_SECRET)"
                        for p in skipped
                    )
                )
            )

