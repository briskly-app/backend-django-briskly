from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = (
        'Bootstrap accounts.User on a database that already ran default Django auth '
        'migrations before AUTH_USER_MODEL was configured.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show planned actions without changing the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        with connection.cursor() as cursor:
            accounts_table_exists = self._table_exists(cursor, 'accounts_user')
            migration_applied = self._migration_applied(cursor)

        if accounts_table_exists and migration_applied:
            self.stdout.write(self.style.SUCCESS('accounts.User is already bootstrapped.'))
            return

        if not migration_applied and self._admin_migrated_before_accounts():
            self.stdout.write(
                'Fixing migration history (accounts.0001_initial must precede admin.0001_initial)...'
            )
            if not dry_run:
                self._insert_accounts_migration_record()

        if not accounts_table_exists:
            self.stdout.write('Creating accounts_user tables...')
            if dry_run:
                self.stdout.write(self._get_accounts_sql())
                return
            self._execute_accounts_sql()

        if not dry_run:
            with connection.cursor() as cursor:
                if not self._migration_applied(cursor):
                    self._insert_accounts_migration_record()

        self.stdout.write(self.style.SUCCESS('accounts.User bootstrap complete.'))
        self.stdout.write(
            'Run: python manage.py migrate --plan  (should show no pending accounts migrations)'
        )

    def _admin_migrated_before_accounts(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM django_migrations
                WHERE app = 'admin' AND name = '0001_initial'
                """
            )
            admin_applied = cursor.fetchone() is not None

            cursor.execute(
                """
                SELECT 1
                FROM django_migrations
                WHERE app = 'accounts' AND name = '0001_initial'
                """
            )
            accounts_applied = cursor.fetchone() is not None

        return admin_applied and not accounts_applied

    def _migration_applied(self, cursor):
        cursor.execute(
            """
            SELECT 1
            FROM django_migrations
            WHERE app = 'accounts' AND name = '0001_initial'
            """
        )
        return cursor.fetchone() is not None

    def _table_exists(self, cursor, table_name):
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = %s
            """,
            [table_name],
        )
        return cursor.fetchone() is not None

    def _insert_accounts_migration_record(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO django_migrations (app, name, applied)
                SELECT 'accounts', '0001_initial', applied - interval '1 day'
                FROM django_migrations
                WHERE app = 'admin' AND name = '0001_initial'
                LIMIT 1
                """
            )
            if cursor.rowcount == 0:
                raise CommandError(
                    'Could not insert accounts.0001_initial — admin.0001_initial is not recorded.'
                )

    def _get_accounts_sql(self):
        out = StringIO()
        call_command('sqlmigrate', 'accounts', '0001', stdout=out)
        return out.getvalue()

    def _execute_accounts_sql(self):
        sql = self._get_accounts_sql()
        statements = [
            statement.strip()
            for statement in sql.replace('BEGIN;', '').replace('COMMIT;', '').split(';')
            if statement.strip()
        ]

        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
