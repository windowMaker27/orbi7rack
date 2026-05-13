"""
seed_demo.py — Crée des colis de démo avec events géocodés et SimulationEngine.

Usage (depuis /backend) :
  docker compose exec backend python scripts/seed_demo.py
  docker compose exec backend python scripts/seed_demo.py --username monuser
  python scripts/seed_demo.py --username monuser

Sans --username : crée/utilise le user 'demo' (password: demo1234).
Avec --username  : attache les colis au user existant spécifié.
"""
import os
import sys
import argparse
import django
from pathlib import Path

# --- Bootstrap Django ---
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.tracking.models import Parcel, TrackingEvent
from apps.tracking.services.simulation_engine import compute_parcel_simulation

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_event(parcel, days_ago, location, lat, lng, status, transport_mode="unknown"):
    timestamp = timezone.now() - timedelta(days=days_ago)
    ev, _ = TrackingEvent.objects.get_or_create(
        parcel=parcel,
        timestamp=timestamp,
        description=status,
        defaults={
            "location": location,
            "latitude": lat,
            "longitude": lng,
            "status": status[:100],
            "transport_mode": transport_mode,
        },
    )
    return ev


# ---------------------------------------------------------------------------
# Données de démo
# ---------------------------------------------------------------------------

DEMO_PARCELS = [
    {
        "tracking_number": "DEMO-CN-FR-001",
        "carrier": "Cainiao",
        "description": "Commande AliExpress (en transit)",
        "origin_country": "CN",
        "dest_country": "FR",
        "status": Parcel.Status.IN_TRANSIT,
        "events": [
            dict(days_ago=6.5,  location="Shenzhen",  lat=22.5431,  lng=114.0579, status="Parcel accepted at origin facility",          transport_mode="road"),
            dict(days_ago=5.8,  location="Shenzhen",  lat=22.5431,  lng=114.0579, status="Departed from origin sorting center",          transport_mode="air"),
            dict(days_ago=5.2,  location="Shanghai",  lat=31.2304,  lng=121.4737, status="Arrived at Shanghai Pudong hub",               transport_mode="air"),
            dict(days_ago=4.5,  location="Shanghai",  lat=31.2304,  lng=121.4737, status="Departed on international flight",             transport_mode="air"),
            dict(days_ago=2.8,  location="Paris CDG", lat=49.0097,  lng=2.5479,   status="Arrived at Paris Charles de Gaulle",           transport_mode="air"),
            dict(days_ago=2.2,  location="Paris CDG", lat=49.0097,  lng=2.5479,   status="Customs clearance in progress",                transport_mode="road"),
            dict(days_ago=1.5,  location="Roissy",    lat=49.0014,  lng=2.5491,   status="Released by customs, handed to La Poste",      transport_mode="road"),
            dict(days_ago=0.8,  location="Paris",     lat=48.8566,  lng=2.3522,   status="In transit to delivery depot",                 transport_mode="road"),
        ],
    },
    {
        "tracking_number": "DEMO-DE-FR-002",
        "carrier": "DHL",
        "description": "Moniteur 27\" (livré)",
        "origin_country": "DE",
        "dest_country": "FR",
        "status": Parcel.Status.DELIVERED,
        "events": [
            dict(days_ago=7.0,  location="Berlin",     lat=52.5200,  lng=13.4050,  status="Shipment picked up",                          transport_mode="road"),
            dict(days_ago=6.3,  location="Leipzig",    lat=51.3397,  lng=12.3731,  status="Processed at Leipzig DHL hub",                 transport_mode="road"),
            dict(days_ago=5.5,  location="Strasbourg", lat=48.5734,  lng=7.7521,   status="Arrived at border facility Strasbourg",        transport_mode="road"),
            dict(days_ago=4.8,  location="Strasbourg", lat=48.5734,  lng=7.7521,   status="Customs cleared, entered France",              transport_mode="road"),
            dict(days_ago=3.5,  location="Paris",      lat=48.8566,  lng=2.3522,   status="Arrived at Paris distribution center",         transport_mode="road"),
            dict(days_ago=2.0,  location="Paris",      lat=48.8566,  lng=2.3522,   status="Out for delivery",                            transport_mode="road"),
            dict(days_ago=1.8,  location="Paris",      lat=48.8566,  lng=2.3522,   status="Successfully delivered",                      transport_mode="road"),
        ],
    },
    {
        "tracking_number": "DEMO-KR-FR-003",
        "carrier": "Korea Post",
        "description": "Figurine collector (livrée)",
        "origin_country": "KR",
        "dest_country": "FR",
        "status": Parcel.Status.DELIVERED,
        "events": [
            dict(days_ago=12.0, location="Seoul",     lat=37.5665,  lng=126.9780, status="Accepted at Seoul post office",               transport_mode="road"),
            dict(days_ago=11.2, location="Incheon",   lat=37.4602,  lng=126.4407, status="Departed from Incheon International Airport", transport_mode="air"),
            dict(days_ago=9.5,  location="Paris CDG", lat=49.0097,  lng=2.5479,   status="Arrived at CDG, customs processing",          transport_mode="air"),
            dict(days_ago=8.8,  location="Paris CDG", lat=49.0097,  lng=2.5479,   status="Customs cleared",                             transport_mode="road"),
            dict(days_ago=7.5,  location="Lyon",      lat=45.7640,  lng=4.8357,   status="In transit to Lyon sorting center",           transport_mode="road"),
            dict(days_ago=6.0,  location="Lyon",      lat=45.7640,  lng=4.8357,   status="Processed at Lyon hub",                      transport_mode="road"),
            dict(days_ago=5.0,  location="Lyon",      lat=45.7640,  lng=4.8357,   status="Out for delivery",                            transport_mode="road"),
            dict(days_ago=4.8,  location="Lyon",      lat=45.7640,  lng=4.8357,   status="Successfully delivered",                      transport_mode="road"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(target_username: str | None = None):
    if target_username:
        # Attache les colis au user existant
        try:
            user = User.objects.get(username=target_username)
            print(f"[seed] User '{target_username}' trouvé (id={user.pk})")
        except User.DoesNotExist:
            print(f"[seed] ERREUR : user '{target_username}' introuvable. Annulation.")
            sys.exit(1)
    else:
        # Crée/récupère le user demo par défaut
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@orbi7rack.local"},
        )
        if created:
            user.set_password("demo1234")
            user.save()
            print("[seed] User 'demo' créé (password: demo1234)")
        else:
            print("[seed] User 'demo' existant")

    for data in DEMO_PARCELS:
        events_data = data.pop("events")

        # Si le colis existe déjà pour un autre owner, on le re-seed pour cet owner
        existing = Parcel.objects.filter(tracking_number=data["tracking_number"]).first()
        if existing and existing.owner == user:
            print(f"[seed] {data['tracking_number']} déjà existant pour '{user.username}', skip")
            data["events"] = events_data
            continue

        # Supprime l'ancien si owner différent (re-seed propre)
        if existing:
            print(f"[seed] {data['tracking_number']} existe pour un autre owner, suppression...")
            existing.delete()

        parcel = Parcel.objects.create(**data, owner=user)
        print(f"[seed] Création {parcel.tracking_number} pour '{user.username}'...")

        for ev_data in events_data:
            make_event(parcel=parcel, **ev_data)

        compute_parcel_simulation(parcel)
        print(f"[seed]   → SimEngine OK ({parcel.events.filter(simulated=True).count()} segments simulés)")

        data["events"] = events_data

    print("[seed] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed colis de démo Orbi7rack")
    parser.add_argument(
        "--username",
        type=str,
        default=None,
        help="Username du compte auquel attacher les colis (défaut: user 'demo')",
    )
    args = parser.parse_args()
    run(target_username=args.username)
