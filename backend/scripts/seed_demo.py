"""
Seed de données de démo — 4 colis sur différents continents
Usage : docker compose exec backend python scripts/seed_demo.py
"""
import os
import sys
import django
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.contrib.auth import get_user_model
from apps.tracking.models import Parcel, TrackingEvent

User = get_user_model()

# --- Chargement du premier user (admin) ---
user = User.objects.first()
if not user:
    print("[ERROR] Aucun utilisateur trouvé. Créez-en un d'abord.")
    sys.exit(1)

print(f"[INFO] Seed pour l'utilisateur : {user.username}")

# --- Nettoyage des données de démo existantes ---
Parcel.objects.filter(tracking_number__startswith="DEMO-").delete()
print("[INFO] Données de démo précédentes supprimées.")

def dt(date_str):
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)


SEED_DATA = [
    {
        "parcel": {
            "tracking_number": "DEMO-KR-FR-001",
            "carrier": "Cainiao",
            "description": "Écouteurs Bluetooth",
            "origin_country": "KR",
            "dest_country": "FR",
            "status": "in_transit",
        },
        "events": [
            {
                "timestamp": dt("2026-04-20T08:00:00"),
                "location": "Dubai",
                "latitude": 25.2048,
                "longitude": 55.2708,
                "status": "Arrived at transit hub",
                "description": "Colis arrivé au hub de transit de Dubaï",
            },
            {
                "timestamp": dt("2026-04-19T14:30:00"),
                "location": "Incheon",
                "latitude": 37.4602,
                "longitude": 126.4407,
                "status": "Departed from origin",
                "description": "Départ de l'aéroport d'Incheon, Seoul",
            },
            {
                "timestamp": dt("2026-04-18T10:00:00"),
                "location": "Seoul",
                "latitude": 37.5665,
                "longitude": 126.9780,
                "status": "Picked up by carrier",
                "description": "Pris en charge par le transporteur à Séoul",
            },
        ],
    },
    {
        "parcel": {
            "tracking_number": "DEMO-CN-US-002",
            "carrier": "DHL",
            "description": "Composants électroniques",
            "origin_country": "CN",
            "dest_country": "US",
            "status": "out_for_delivery",
        },
        "events": [
            {
                "timestamp": dt("2026-04-20T07:15:00"),
                "location": "Los Angeles",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "status": "Out for delivery",
                "description": "En cours de livraison à Los Angeles",
            },
            {
                "timestamp": dt("2026-04-19T23:00:00"),
                "location": "Los Angeles",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "status": "Arrived at delivery facility",
                "description": "Arrivé au centre de distribution de LA",
            },
            {
                "timestamp": dt("2026-04-18T12:00:00"),
                "location": "Shanghai",
                "latitude": 31.2304,
                "longitude": 121.4737,
                "status": "Departed from origin country",
                "description": "Départ de Shanghai vers les États-Unis",
            },
            {
                "timestamp": dt("2026-04-17T09:00:00"),
                "location": "Shenzhen",
                "latitude": 22.5431,
                "longitude": 114.0579,
                "status": "Processing at sorting center",
                "description": "Tri au centre de Shenzhen",
            },
        ],
    },
    {
        "parcel": {
            "tracking_number": "DEMO-JP-DE-003",
            "carrier": "FedEx",
            "description": "Figurine collector",
            "origin_country": "JP",
            "dest_country": "DE",
            "status": "in_transit",
        },
        "events": [
            {
                "timestamp": dt("2026-04-20T05:45:00"),
                "location": "Frankfurt",
                "latitude": 50.1109,
                "longitude": 8.6821,
                "status": "Customs clearance in progress",
                "description": "Dédouanement en cours à Francfort",
            },
            {
                "timestamp": dt("2026-04-19T18:00:00"),
                "location": "Narita",
                "latitude": 35.7720,
                "longitude": 140.3929,
                "status": "Departed from Japan",
                "description": "Départ de l'aéroport de Narita, Tokyo",
            },
            {
                "timestamp": dt("2026-04-17T11:00:00"),
                "location": "Tokyo",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "status": "Picked up",
                "description": "Colis collecté à Tokyo",
            },
        ],
    },
    {
        "parcel": {
            "tracking_number": "DEMO-BR-FR-004",
            "carrier": "Correios",
            "description": "Café spécialité",
            "origin_country": "BR",
            "dest_country": "FR",
            "status": "pending",
        },
        "events": [
            {
                "timestamp": dt("2026-04-20T06:00:00"),
                "location": "São Paulo",
                "latitude": -23.5505,
                "longitude": -46.6333,
                "status": "Accepted by carrier",
                "description": "Pris en charge par Correios à São Paulo",
            },
        ],
    },
]

# --- Insertion ---
for entry in SEED_DATA:
    parcel = Parcel.objects.create(owner=user, **entry["parcel"])
    for ev in entry["events"]:
        TrackingEvent.objects.create(parcel=parcel, **ev)
    print(f"[OK] {parcel.tracking_number} — {parcel.status} ({len(entry['events'])} events)")

print(f"\n[DONE] {len(SEED_DATA)} colis de démo créés.")
