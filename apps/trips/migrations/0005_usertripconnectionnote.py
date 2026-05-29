from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0004_usertrip_user_not_null'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserTripConnectionNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence_id', models.PositiveIntegerField()),
                ('html_source', models.TextField(blank=True, default='')),
                ('image_url', models.URLField(blank=True, default='', max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'user_trip_connection',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notes',
                        to='trips.usertripconnection',
                    ),
                ),
            ],
            options={
                'db_table': 'routes_usertripconnectionnote',
                'ordering': ['sequence_id', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='usertripconnectionnote',
            constraint=models.UniqueConstraint(
                fields=('user_trip_connection', 'sequence_id'),
                name='unique_note_sequence_per_connection',
            ),
        ),
        migrations.AddConstraint(
            model_name='usertripconnectionnote',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ('html_source__gt', ''),
                    ('image_url', ''),
                ) | models.Q(
                    ('html_source', ''),
                    ('image_url__gt', ''),
                ),
                name='note_exactly_one_content_type',
            ),
        ),
    ]
