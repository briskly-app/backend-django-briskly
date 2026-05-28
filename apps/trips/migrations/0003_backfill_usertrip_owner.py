from django.db import migrations


def backfill_trip_owner(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    UserTrip = apps.get_model('trips', 'UserTrip')

    user, _ = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'testuser@example.com'},
    )

    UserTrip.objects.filter(user__isnull=True).update(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ('trips', '0002_usertrip_user'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_trip_owner, migrations.RunPython.noop),
    ]

