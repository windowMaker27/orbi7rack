"""
Usage:
  python manage.py seed_demo
  python manage.py seed_demo --user admin
  python manage.py seed_demo --reset   # supprime et recrée

Colis démo :
  - DEMO-AF6728-CDG-PEK  : vol AF6728, Paris → Pékin
  - DEMO-AF652-CDG-RUN   : vol AF652,  Paris CDG → La Réunion
  - DEMO-KZ101-LAX-NRT   : vol KZ101,  Los Angeles → Tokyo Narita
  - DEMO-DE2291-CPT-FRA  : vol DE2291, Le Cap → Francfort

Idempotent : ne crée pas de doublon si le tracking number existe déjà.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tracking.models import Parcel, TrackingEvent

# ---------------------------------------------------------------------------
# Définition des colis démo
# ---------------------------------------------------------------------------
DEMO_PARCELS = [
    {
        "tracking_number": "DEMO-AF6728-CDG-PEK",
        "carrier": "Air France Cargo",
        "description": "[DEMO] Colis suivi sur vol AF6728",
        "origin_country": "CDG",
        "dest_country": "PEK",
        "status": "in_transit",
        "flight_number": "AF6728",
        "events": [
            {
                "status": "in_transit",
                "description": "Colis pris en charge — Aéroport Charles de Gaulle",
                "location": "Paris CDG, France",
                "latitude": 49.0097, "longitude": 2.5479,
                "delta_hours": -6,
            },
            {
                "status": "in_transit",
                "description": "Chargement vol AF6728 — départ CDG",
                "location": "Paris CDG, France",
                "latitude": 49.0097, "longitude": 2.5479,
                "delta_hours": -2,
            },
            {
                "status": "in_transit",
                "description": "En vol — survol de la Russie",
                "location": "En vol",
                "latitude": 55.75, "longitude": 60.0,
                "delta_hours": 0,
            },
        ],
    },
    {
        "tracking_number": "DEMO-AF652-CDG-RUN",
        "carrier": "Air France Cargo",
        "description": "[DEMO] Fret AF652 Paris → La Réunion",
        "origin_country": "CDG",
        "dest_country": "RUN",
        "status": "in_transit",
        "flight_number": "AF652",
        "events": [
            {
                "status": "in_transit",
                "description": "Enlèvement aéroport Charles de Gaulle",
                "location": "Paris CDG, France",
                "latitude": 49.0097, "longitude": 2.5479,
                "delta_hours": -10,
            },
            {
                "status": "in_transit",
                "description": "Décollage vol AF652 — CDG",
                "location": "Paris CDG, France",
                "latitude": 49.0097, "longitude": 2.5479,
                "delta_hours": -9,
            },
            {
                "status": "in_transit",
                "description": "En vol — survol de l'océan Indien",
                "location": "En vol",
                "latitude": -20.0, "longitude": 55.0,
                "delta_hours": -1,
            },
        ],
    },
    {
        "tracking_number": "DEMO-KZ101-LAX-NRT",
        "carrier": "Air Astana Cargo",
        "description": "[DEMO] Fret KZ101 Los Angeles → Tokyo Narita",
        "origin_country": "LAX",
        "dest_country": "NRT",
        "status": "in_transit",
        "flight_number": "KZ101",
        "events": [
            {
                "status": "in_transit",
                "description": "Prise en charge — Los Angeles International",
                "location": "Los Angeles LAX, USA",
                "latitude": 33.9425, "longitude": -118.4081,
                "delta_hours": -7,
            },
            {
                "status": "in_transit",
                "description": "Départ vol KZ101 — LAX",
                "location": "Los Angeles LAX, USA",
                "latitude": 33.9425, "longitude": -118.4081,
                "delta_hours": -6,
            },
            {
                "status": "in_transit",
                "description": "En vol — survol du Pacifique Nord",
                "location": "En vol",
                "latitude": 45.0, "longitude": -160.0,
                "delta_hours": -2,
            },
        ],
    },
    {
        "tracking_number": "DEMO-DE2291-CPT-FRA",
        "carrier": "Condor Cargo",
        "description": "[DEMO] Fret DE2291 Le Cap → Francfort",
        "origin_country": "CPT",
        "dest_country": "FRA",
        "status": "in_transit",
        "flight_number": "DE2291",
        "events": [
            {
                "status": "in_transit",
                "description": "Enlèvement aéroport du Cap (CPT)",
                "location": "Le Cap CPT, Afrique du Sud",
                "latitude": -33.9715, "longitude": 18.6021,
                "delta_hours": -8,
            },
            {
                "status": "in_transit",
                "description": "Décollage vol DE2291 — CPT",
                "location": "Le Cap CPT, Afrique du Sud",
                "latitude": -33.9715, "longitude": 18.6021,
                "delta_hours": -7,
            },
            {
                "status": "in_transit",
                "description": "En vol — survol de l'Afrique centrale",
                "location": "En vol",
                "latitude": 5.0, "longitude": 20.0,
                "delta_hours": -3,
            },
        ],
    },
]

# Clé de destination -> code ISO2 pour les pays non couverts par ISO2_CENTROIDS du globe
DEST_ISO2_MAP = {
    "RUN": "RE",  # La Réunion → île, pas dans ISO2_CENTROIDS — garde RUN (mappé dans Globe)
    "NRT": "JP",  # Tokyo Narita
    "FRA": "DE",  # Francfort
    "CPT": "ZA",  # Le Cap
    "CDG": "FR",  # Paris
    "PEK": "CN",  # Pékin
    "LAX": "US",  # Los Angeles
}


class Command(BaseCommand):
    help = "Crée les colis démo (AF6728, AF652, KZ101, DE2291)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            default="",
            help="Username du propriétaire (défaut: premier superuser ou premier user)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les colis existants avant de les recréer",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        username = options["user"]
        if username:
            try:
                owner = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Utilisateur '{username}' introuvable."))
                return
        else:
            owner = (
                User.objects.filter(is_superuser=True).first()
                or User.objects.first()
            )
            if not owner:
                self.stderr.write(self.style.ERROR("Aucun utilisateur en base. Créez-en un d'abord."))
                return

        now = timezone.now()
        created_count = 0
        skipped_count = 0

        for demo in DEMO_PARCELS:
            tn = demo["tracking_number"]

            if options["reset"]:
                deleted, _ = Parcel.objects.filter(tracking_number=tn).delete()
                if deleted:
                    self.stdout.write(self.style.WARNING(f"Supprimé : {tn}"))

            if Parcel.objects.filter(tracking_number=tn).exists():
                self.stdout.write(self.style.WARNING(f"Déjà présent (skip) : {tn}"))
                skipped_count += 1
                continue

            parcel = Parcel.objects.create(
                tracking_number=tn,
                carrier=demo["carrier"],
                description=demo["description"],
                origin_country=demo["origin_country"],
                dest_country=demo["dest_country"],
                status=demo["status"],
                owner=owner,
                flight_number=demo["flight_number"],
                last_synced_at=now,
            )

            for ev in demo["events"]:
                TrackingEvent.objects.create(
                    parcel=parcel,
                    timestamp=now + timezone.timedelta(hours=ev["delta_hours"]),
                    location=ev["location"],
                    latitude=ev["latitude"],
                    longitude=ev["longitude"],
                    status=ev["status"],
                    description=ev["description"],
                )

            self.stdout.write(self.style.SUCCESS(f"✅ Créé : {tn} (vol {demo['flight_number']})"))
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé — {created_count} créé(s), {skipped_count} ignoré(s). Owner: {owner.username}"
        ))
