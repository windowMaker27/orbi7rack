"""
Seed de données de démo — 4 colis sur différents continents + 2 colis live
  - DEMO-LIVE-SQ335 : Paris CDG → Singapore Changi (atterri)
  - DEMO-LIVE-UA984 : Paris CDG → San Francisco SFO (en vol, décollage 07:21 UTC)
Crée automatiquement un superuser admin/admin si inexistant.
Usage : docker compose exec backend python scripts/seed_demo.py
        ou : make seed-demo
"""
import os
import sys
import django
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.tracking.models import Parcel, TrackingEvent

User = get_user_model()

# --- Création automatique de l'admin si inexistant ---
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(username="admin", email="admin@orbi7rack.local", password="admin")
    print("[INFO] Superuser admin/admin créé.")
else:
    print("[INFO] Superuser admin déjà existant.")

user = User.objects.get(username="admin")
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
    # --- Colis LIVE lié au vol SQ335 (Paris CDG → Singapore Changi) ---
    # Boeing 777-312(ER) Singapore Airlines, ~13h de vol
    {
        "parcel": {
            "tracking_number": "DEMO-LIVE-SQ335",
            "carrier": "Singapore Airlines Cargo",
            "description": "Composants semiconducteurs [LIVE]",
            "origin_country": "FR",
            "dest_country": "SG",
            "status": "in_transit",
            "flight_number": "SQ335",
        },
        "events": [
            {
                "timestamp": dt("2026-04-21T06:00:00"),
                "location": "Singapore Changi Airport",
                "latitude": 1.3644,
                "longitude": 103.9915,
                "status": "Expected arrival",
                "description": "Arrivée prévue à l'aéroport de Changi, Singapour",
            },
            {
                "timestamp": dt("2026-04-20T22:10:00"),
                "location": "Paris Charles de Gaulle",
                "latitude": 49.0097,
                "longitude": 2.5479,
                "status": "Departed on flight SQ335",
                "description": "Départ de Paris CDG sur le vol SQ335 (Boeing 777)",
            },
            {
                "timestamp": dt("2026-04-20T18:00:00"),
                "location": "Paris CDG - Fret",
                "latitude": 49.0097,
                "longitude": 2.5479,
                "status": "Loaded on aircraft",
                "description": "Chargé en soute sur le Boeing 777-312(ER)",
            },
            {
                "timestamp": dt("2026-04-20T10:00:00"),
                "location": "Paris CDG - Fret",
                "latitude": 49.0097,
                "longitude": 2.5479,
                "status": "Customs cleared",
                "description": "Dédouanement export validé à Paris",
            },
        ],
    },
    # --- Colis LIVE lié au vol UA984 (Paris CDG → San Francisco SFO) ---
    # Boeing 787-9 United Airlines, ~11h de vol
    # Décollage réel : 22 avril 2026 à 07:21 UTC (09:21 CEST)
    {
        "parcel": {
            "tracking_number": "DEMO-LIVE-UA984",
            "carrier": "United Airlines Cargo",
            "description": "Équipements optiques [LIVE]",
            "origin_country": "FR",
            "dest_country": "US",
            "status": "in_transit",
            "flight_number": "UA984",
        },
        "events": [
            {
                "timestamp": dt("2026-04-22T18:30:00"),
                "location": "San Francisco International Airport",
                "latitude": 37.6213,
                "longitude": -122.3790,
                "status": "Expected arrival",
                "description": "Arrivée prévue à SFO — ~11h de vol depuis CDG",
            },
            {
                "timestamp": dt("2026-04-22T07:21:00"),
                "location": "Paris Charles de Gaulle",
                "latitude": 49.0097,
                "longitude": 2.5479,
                "status": "Departed on flight UA984",
                "description": "Départ de Paris CDG sur le vol UA984 (Boeing 787-9 Dreamliner)",
            },
            {
                "timestamp": dt("2026-04-22T04:00:00"),
                "location": "Paris CDG - Fret",
                "latitude": 49.0097,
                "longitude": 2.5479,
                "status": "Loaded on aircraft",
                "description": "Chargé en soute sur le Boeing 787-9",
            },
            {
                "timestamp": dt("2026-04-21T20:00:00"),
                "location": "Paris CDG - Fret",
                "latitude": 49.0097,
                "longitude": 2.5479,
                "status": "Customs cleared",
                "description": "Dédouanement export validé à Paris",
            },
        ],
    },
]

# --- Insertion ---
for entry in SEED_DATA:
    parcel_data = entry["parcel"]
    parcel = Parcel.objects.create(owner=user, **parcel_data)
    for ev in entry["events"]:
        TrackingEvent.objects.create(parcel=parcel, **ev)
    flight = parcel_data.get("flight_number", "")
    flight_info = f" ✈️  vol {flight}" if flight else ""
    print(f"[OK] {parcel.tracking_number} — {parcel.status} ({len(entry['events'])} events){flight_info}")

print(f"\n[DONE] {len(SEED_DATA)} colis de démo créés.")
