from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0005_usertripconnectionnote'),
    ]

    operations = [
        migrations.AddField(
            model_name='usertrip',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
    ]
