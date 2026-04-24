"""
seed_demo.py — Crée un colis de démo lié à un ou plusieurs vols réels.

Usage:
  # Auto-lookup origine/destination via AviationStack (nécessite AVIATIONSTACK_API_KEY)
  python scripts/seed_demo.py AF011 BA306

  # Avec origine/destination manuels (bypass API)
  python scripts/seed_demo.py AF011:CDG:JFK BA306:LHR:CDG

  # Format mixte : AF011 auto-lookup, BA306 manuel
  python scripts/seed_demo.py AF011 BA306:LHR:CDG

Variables d'environnement:
  AVIATIONSTACK_API_KEY   — clé API AviationStack (optionnel, fallback = saisie manuelle)
  AVIATIONSTACK_BASE_URL  — défaut: http://api.aviationstack.com/v1
"""
import os
import sys
import django
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.tracking.models import Parcel, TrackingEvent

User = get_user_model()

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
AVIATION_API_KEY  = os.environ.get("AVIATIONSTACK_API_KEY", "")
AVIATION_BASE_URL = os.environ.get("AVIATIONSTACK_BASE_URL", "http://api.aviationstack.com/v1")

# Mapping IATA aéroport → (pays ISO2, lat, lng)
IATA_META: dict[str, dict] = {
    "CDG": {"country": "FR", "lat": 49.0097,  "lng":   2.5479, "name": "Paris Charles de Gaulle"},
    "ORY": {"country": "FR", "lat": 48.7262,  "lng":   2.3652, "name": "Paris Orly"},
    "LHR": {"country": "GB", "lat": 51.4775,  "lng":  -0.4614, "name": "London Heathrow"},
    "JFK": {"country": "US", "lat": 40.6413,  "lng": -73.7781, "name": "New York JFK"},
    "LAX": {"country": "US", "lat": 33.9425,  "lng":-118.4081, "name": "Los Angeles"},
    "SFO": {"country": "US", "lat": 37.6213,  "lng":-122.3790, "name": "San Francisco"},
    "ORD": {"country": "US", "lat": 41.9742,  "lng": -87.9073, "name": "Chicago O'Hare"},
    "DXB": {"country": "AE", "lat": 25.2532,  "lng":  55.3657, "name": "Dubai Intl"},
    "SIN": {"country": "SG", "lat":  1.3644,  "lng": 103.9915, "name": "Singapore Changi"},
    "HKG": {"country": "HK", "lat": 22.3080,  "lng": 113.9185, "name": "Hong Kong Intl"},
    "PEK": {"country": "CN", "lat": 40.0799,  "lng": 116.6031, "name": "Beijing Capital"},
    "PVG": {"country": "CN", "lat": 31.1443,  "lng": 121.8083, "name": "Shanghai Pudong"},
    "ICN": {"country": "KR", "lat": 37.4602,  "lng": 126.4407, "name": "Seoul Incheon"},
    "NRT": {"country": "JP", "lat": 35.7647,  "lng": 140.3864, "name": "Tokyo Narita"},
    "HND": {"country": "JP", "lat": 35.5494,  "lng": 139.7798, "name": "Tokyo Haneda"},
    "FRA": {"country": "DE", "lat": 50.0379,  "lng":   8.5622, "name": "Frankfurt Intl"},
    "AMS": {"country": "NL", "lat": 52.3086,  "lng":   4.7639, "name": "Amsterdam Schiphol"},
    "MAD": {"country": "ES", "lat": 40.4983,  "lng":  -3.5676, "name": "Madrid Barajas"},
    "FCO": {"country": "IT", "lat": 41.8003,  "lng":  12.2389, "name": "Rome Fiumicino"},
    "ZRH": {"country": "CH", "lat": 47.4647,  "lng":   8.5492, "name": "Zurich"},
    "BCN": {"country": "ES", "lat": 41.2971,  "lng":   2.0785, "name": "Barcelona El Prat"},
    "BRU": {"country": "BE", "lat": 50.9010,  "lng":   4.4844, "name": "Brussels Zaventem"},
    "GRU": {"country": "BR", "lat": -23.4356, "lng": -46.4731, "name": "São Paulo Guarulhos"},
    "EZE": {"country": "AR", "lat": -34.8222, "lng": -58.5358, "name": "Buenos Aires Ezeiza"},
    "BOG": {"country": "CO", "lat":   4.7016,  "lng": -74.1469, "name": "Bogotá El Dorado"},
    "MEX": {"country": "MX", "lat":  19.4363,  "lng": -99.0721, "name": "Mexico City Intl"},
    "YYZ": {"country": "CA", "lat":  43.6777,  "lng": -79.6248, "name": "Toronto Pearson"},
    "YUL": {"country": "CA", "lat":  45.4706,  "lng": -73.7408, "name": "Montreal Trudeau"},
    "SYD": {"country": "AU", "lat": -33.9461, "lng": 151.1772, "name": "Sydney Kingsford Smith"},
    "MEL": {"country": "AU", "lat": -37.6690, "lng": 144.8410, "name": "Melbourne Tullamarine"},
    "CPT": {"country": "ZA", "lat": -33.9715, "lng":  18.6021, "name": "Cape Town Intl"},
    "JNB": {"country": "ZA", "lat": -26.1367, "lng":  28.2411, "name": "Johannesburg OR Tambo"},
    "CAI": {"country": "EG", "lat":  30.1219, "lng":  31.4056, "name": "Cairo Intl"},
    "IST": {"country": "TR", "lat":  41.2753, "lng":  28.7519, "name": "Istanbul Airport"},
    "DOH": {"country": "QA", "lat":  25.2731, "lng":  51.6081, "name": "Doha Hamad Intl"},
    "AUH": {"country": "AE", "lat":  24.4330, "lng":  54.6511, "name": "Abu Dhabi Intl"},
    "BKK": {"country": "TH", "lat":  13.6900, "lng": 100.7501, "name": "Bangkok Suvarnabhumi"},
    "KUL": {"country": "MY", "lat":   2.7456, "lng": 101.7099, "name": "Kuala Lumpur Intl"},
    "MNL": {"country": "PH", "lat":  14.5086, "lng": 121.0197, "name": "Manila Ninoy Aquino"},
    "CGK": {"country": "ID", "lat":  -6.1256, "lng": 106.6559, "name": "Jakarta Soekarno-Hatta"},
    "DEL": {"country": "IN", "lat":  28.5562, "lng":  77.1000, "name": "Delhi Indira Gandhi"},
    "BOM": {"country": "IN", "lat":  19.0896, "lng":  72.8656, "name": "Mumbai Chhatrapati Shivaji"},
    "RUN": {"country": "RE", "lat": -20.8872, "lng":  55.5136, "name": "La Réunion Roland Garros"},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def iata_meta(code: str) -> dict | None:
    return IATA_META.get(code.upper())


def lookup_flight_api(flight_number: str) -> dict | None:
    """Tente de récupérer origine/destination via AviationStack.
    Retourne {origin_iata, dest_iata, airline, status} ou None.
    """
    if not AVIATION_API_KEY:
        return None
    try:
        resp = requests.get(
            f"{AVIATION_BASE_URL}/flights",
            params={"access_key": AVIATION_API_KEY, "flight_iata": flight_number},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        flights = data.get("data", [])
        if not flights:
            return None
        f = flights[0]
        return {
            "origin_iata":  f["departure"]["iata"],
            "dest_iata":    f["arrival"]["iata"],
            "airline":      f["airline"]["name"],
            "flight_status": f.get("flight_status", "active"),
        }
    except Exception as e:
        print(f"[WARN] AviationStack lookup échoué pour {flight_number}: {e}")
        return None


def ask_iata(prompt: str) -> str:
    while True:
        val = input(prompt).strip().upper()
        if len(val) == 3:
            return val
        print("  → Code IATA invalide (3 lettres attendues).")


def resolve_flight(token: str) -> dict:
    """
    token peut être :
      - "AF011"            → lookup API puis saisie si échec
      - "AF011:CDG:JFK"    → bypass direct
    Retourne dict avec flight_number, origin_iata, dest_iata, airline.
    """
    parts = token.split(":")
    flight_number = parts[0].upper()

    if len(parts) == 3:
        # Fourni manuellement
        _, origin_iata, dest_iata = parts
        return {
            "flight_number": flight_number,
            "origin_iata":   origin_iata.upper(),
            "dest_iata":     dest_iata.upper(),
            "airline":       "",
        }

    # Tentative API
    print(f"[INFO] Lookup API pour {flight_number}…")
    api_result = lookup_flight_api(flight_number)
    if api_result:
        print(f"  ✓ {flight_number}: {api_result['origin_iata']} → {api_result['dest_iata']} ({api_result['airline']})")
        return {"flight_number": flight_number, **api_result}

    # Fallback saisie manuelle
    print(f"  ✗ Lookup échoué ou API key absente. Saisie manuelle pour {flight_number}:")
    origin_iata = ask_iata(f"  Code IATA aéroport d'origine  : ")
    dest_iata   = ask_iata(f"  Code IATA aéroport de destination : ")
    return {
        "flight_number": flight_number,
        "origin_iata":   origin_iata,
        "dest_iata":     dest_iata,
        "airline":       "",
    }


def create_parcel_for_flight(user, flight: dict) -> None:
    fn   = flight["flight_number"]
    orig = iata_meta(flight["origin_iata"])
    dest = iata_meta(flight["dest_iata"])

    if not orig:
        print(f"  [WARN] IATA '{flight['origin_iata']}' inconnu dans le mapping local — pays sera '{flight['origin_iata']}'.")
    if not dest:
        print(f"  [WARN] IATA '{flight['dest_iata']}' inconnu dans le mapping local — pays sera '{flight['dest_iata']}'.")

    origin_country = (orig or {}).get("country", flight["origin_iata"])
    dest_country   = (dest or {}).get("country", flight["dest_iata"])
    origin_name    = (orig or {}).get("name", flight["origin_iata"])
    dest_name      = (dest or {}).get("name", flight["dest_iata"])

    tracking_number = f"DEMO-LIVE-{fn}"

    # Supprime si déjà existant
    Parcel.objects.filter(tracking_number=tracking_number).delete()

    airline = flight.get("airline") or "Unknown Airline"

    parcel = Parcel.objects.create(
        owner=user,
        tracking_number=tracking_number,
        carrier=airline,
        description=f"Colis démo lié au vol {fn} [LIVE]",
        origin_country=origin_country,
        dest_country=dest_country,
        status="in_transit",
        flight_number=fn,
    )

    t = now_utc()
    events = []

    if orig:
        events.append(TrackingEvent(
            parcel=parcel,
            timestamp=t.replace(hour=max(0, t.hour - 2)),
            location=origin_name,
            latitude=orig["lat"],
            longitude=orig["lng"],
            status=f"Departed on flight {fn}",
            description=f"Départ de {origin_name} sur le vol {fn}",
        ))

    if dest:
        events.append(TrackingEvent(
            parcel=parcel,
            timestamp=t.replace(hour=(t.hour + 8) % 24),
            location=dest_name,
            latitude=dest["lat"],
            longitude=dest["lng"],
            status="Expected arrival",
            description=f"Arrivée prévue à {dest_name}",
        ))

    TrackingEvent.objects.bulk_create(events)
    print(f"[OK] {tracking_number} — {origin_country} → {dest_country} — vol {fn} ({len(events)} events)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

# Admin
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(username="admin", email="admin@orbi7rack.local", password="admin")
    print("[INFO] Superuser admin/admin créé.")
else:
    print("[INFO] Superuser admin déjà existant.")

user = User.objects.get(username="admin")
print(f"[INFO] Seed pour l'utilisateur : {user.username}\n")

flight_tokens = sys.argv[1:]
print(f"[INFO] {len(flight_tokens)} vol(s) à traiter : {', '.join(flight_tokens)}\n")

for token in flight_tokens:
    flight = resolve_flight(token)
    create_parcel_for_flight(user, flight)

print(f"\n[DONE] {len(flight_tokens)} colis créé(s).")
