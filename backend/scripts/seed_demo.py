"""
seed_demo.py — Crée des colis de démo avec events géocodés et SimulationEngine.

Usage (depuis /backend) :
  docker compose exec backend python scripts/seed_demo.py
  # ou
  python scripts/seed_demo.py   (avec DJANGO_SETTINGS_MODULE positionné)

Crée (ou récupère) un user demo, puis 3 colis avec events géocodés
variés : un en transit CN→FR, un livré DE→FR, un livré KR→FR.
Appelle compute_parcel_simulation() après chaque création.
"""
import os
import sys
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

def run():
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

        parcel, p_created = Parcel.objects.get_or_create(
            tracking_number=data["tracking_number"],
            defaults={**data, "owner": user},
        )
        if not p_created:
            print(f"[seed] {parcel.tracking_number} déjà existant, skip")
            data["events"] = events_data
            continue

        print(f"[seed] Création {parcel.tracking_number}...")

        for ev_data in events_data:
            make_event(parcel=parcel, **ev_data)

        compute_parcel_simulation(parcel)
        print(f"[seed]   → SimEngine OK ({parcel.events.filter(simulated=True).count()} segments simulés)")

        data["events"] = events_data

    print("[seed] Done.")


if __name__ == "__main__":
    run()
