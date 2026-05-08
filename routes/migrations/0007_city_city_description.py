# Generated manually for city_description

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0006_usertripconnection'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='city_description',
            field=models.TextField(
                blank=True,
                null=True,
            ),
        ),
    ]
