# Generated manually — Étape 1
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracking", "0004_parcel_dest_coords_parcel_origin_coords"),
    ]

    operations = [
        migrations.AddField(
            model_name="trackingevent",
            name="flight_iata",
            field=models.CharField(
                max_length=10,
                blank=True,
                null=True,
                help_text="Code IATA du vol extrait (ex: UA123, AF447)",
            ),
        ),
        migrations.AddField(
            model_name="trackingevent",
            name="transport_mode",
            field=models.CharField(
                max_length=20,
                blank=True,
                default="unknown",
                choices=[
                    ("air", "Aérien"),
                    ("road", "Terrestre"),
                    ("sea", "Maritime"),
                    ("unknown", "Inconnu"),
                ],
                help_text="Mode de transport détecté pour cet événement",
            ),
        ),
    ]
