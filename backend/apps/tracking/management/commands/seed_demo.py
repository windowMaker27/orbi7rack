"""
Usage:
  python manage.py seed_demo
  python manage.py seed_demo --user admin
  python manage.py seed_demo --reset   # supprime et recéé

Ajoute un colis démo lié au vol AF6728 (CDG -> PEK).
Idempotent : ne crée pas de doublon si le tracking number existe déjà.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tracking.models import Parcel, TrackingEvent

TRACKING_NUMBER = "DEMO-AF6728-CDG-PEK"

EVENTS = [
    {
        "status": "in_transit",
        "description": "Colis pris en charge — Aéroport Charles de Gaulle",
        "location": "Paris CDG, France",
        "latitude": 49.0097,
        "longitude": 2.5479,
        "delta_hours": -6,
    },
    {
        "status": "in_transit",
        "description": "Chargement vol AF6728 — départ CDG",
        "location": "Paris CDG, France",
        "latitude": 49.0097,
        "longitude": 2.5479,
        "delta_hours": -2,
    },
    {
        "status": "in_transit",
        "description": "En vol — survol de la Russie",
        "location": "En vol",
        "latitude": 55.75,
        "longitude": 60.0,
        "delta_hours": 0,
    },
]


class Command(BaseCommand):
    help = "Crée un colis démo AF6728 (CDG -> PEK) pour le suivi live"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            default="",
            help="Username du propriétaire (défaut: premier superuser ou premier user)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime le colis existant avant de le recréer",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        # Résolution du user
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

        # Reset optionnel
        if options["reset"]:
            deleted, _ = Parcel.objects.filter(tracking_number=TRACKING_NUMBER).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f"Colis {TRACKING_NUMBER} supprimé (reset)."))

        # Idempotence
        if Parcel.objects.filter(tracking_number=TRACKING_NUMBER).exists():
            self.stdout.write(self.style.WARNING(
                f"Colis {TRACKING_NUMBER} déjà présent — rien à faire. (--reset pour forcer)"
            ))
            return

        now = timezone.now()

        parcel = Parcel.objects.create(
            tracking_number=TRACKING_NUMBER,
            carrier="Air France Cargo",
            description="[DEMO] Colis suivi sur vol AF6728",
            origin_country="FR",   # ISO-2 obligatoire pour _country_centroid()
            dest_country="CN",     # ISO-2 obligatoire pour _country_centroid()
            status=Parcel.Status.IN_TRANSIT,
            owner=owner,
            flight_number="AF6728",
            last_synced_at=now,
        )

        for ev in EVENTS:
            TrackingEvent.objects.create(
                parcel=parcel,
                timestamp=now + timezone.timedelta(hours=ev["delta_hours"]),
                location=ev["location"],
                latitude=ev["latitude"],
                longitude=ev["longitude"],
                status=ev["status"],
                description=ev["description"],
            )

        self.stdout.write(self.style.SUCCESS(
            f"✅ Colis démo créé : {TRACKING_NUMBER} (owner: {owner.username}, vol: AF6728 CDG->PEK)"
        ))
