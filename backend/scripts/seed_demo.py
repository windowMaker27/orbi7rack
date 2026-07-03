"""
seed_demo.py — Crée un colis de démo lié à un vol live.

Crée 2 events minimum (départ + arrivée estimée) géocodés depuis les
aimséroports IATA du vol, ce qui permet au SimulationEngine de former
un arc et une position simulée.

Usage (depuis /backend) :
  docker compose exec backend python scripts/seed_demo.py --flight AF011
  docker compose exec backend python scripts/seed_demo.py --flight AF011 --username monuser
  docker compose exec backend python scripts/seed_demo.py --flight AF011 --origin CDG --dest JFK --force

Arguments :
  --flight      OBLIGATOIRE. Numéro de vol IATA (ex: AF011, UA123).
  --origin      Code IATA de l'aéroport de départ (ex: CDG). Optionnel.
  --dest        Code IATA de l'aéroport d'arrivée (ex: JFK). Optionnel.
  --username    Attache le colis à un user existant (défaut: user 'demo').
  --tracking    Numéro de tracking custom (défaut: généré depuis le vol).
  --description Description du colis (défaut: "Colis démo <flight>").
  --carrier     Transporteur (défaut: extrait du préfixe IATA du vol).
  --force       Supprime le colis existant avec ce tracking_number et le recrée.
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
# Lookups statiques
# ---------------------------------------------------------------------------

IATA_CARRIERS = {
    "AF": "Air France",     "UA": "United Airlines", "AA": "American Airlines",
    "BA": "British Airways","LH": "Lufthansa",       "EK": "Emirates",
    "QR": "Qatar Airways",  "DL": "Delta Air Lines", "KL": "KLM",
    "IB": "Iberia",         "TK": "Turkish Airlines","SQ": "Singapore Airlines",
    "CX": "Cathay Pacific", "NH": "ANA",             "JL": "Japan Airlines",
    "CA": "Air China",      "MU": "China Eastern",   "CZ": "China Southern",
    "KE": "Korean Air",     "OZ": "Asiana Airlines", "AC": "Air Canada",
    "QF": "Qantas",         "EY": "Etihad",          "FX": "FedEx",
}

# Aéroports IATA les plus courants : (lat, lng, nom, iso_country)
AIRPORTS = {
    "CDG": (49.0097,   2.5479,   "Paris Charles de Gaulle", "FR"),
    "ORY": (48.7233,   2.3794,   "Paris Orly",              "FR"),
    "JFK": (40.6413,  -73.7781,  "New York JFK",            "US"),
    "LAX": (33.9425, -118.4081,  "Los Angeles",             "US"),
    "ORD": (41.9742,  -87.9073,  "Chicago O'Hare",          "US"),
    "LHR": (51.4700,  -0.4543,   "London Heathrow",         "GB"),
    "FRA": (50.0379,   8.5622,   "Frankfurt",               "DE"),
    "AMS": (52.3086,   4.7639,   "Amsterdam Schiphol",      "NL"),
    "DXB": (25.2532,  55.3657,   "Dubai",                   "AE"),
    "SIN": ( 1.3644,  103.9915,  "Singapore Changi",        "SG"),
    "HKG": (22.3080,  113.9185,  "Hong Kong",               "HK"),
    "NRT": (35.7647,  140.3864,  "Tokyo Narita",            "JP"),
    "HND": (35.5494,  139.7798,  "Tokyo Haneda",            "JP"),
    "ICN": (37.4602,  126.4407,  "Seoul Incheon",           "KR"),
    "PVG": (31.1434,  121.8052,  "Shanghai Pudong",         "CN"),
    "PEK": (40.0799,  116.6031,  "Beijing Capital",         "CN"),
    "SZX": (22.6395,  113.8145,  "Shenzhen",                "CN"),
    "CAN": (23.3924,  113.2988,  "Guangzhou",               "CN"),
    "SYD": (-33.9399, 151.1753,  "Sydney",                  "AU"),
    "GRU": (-23.4356, -46.4731,  "São Paulo",               "BR"),
    "YYZ": (43.6777,  -79.6248,  "Toronto Pearson",         "CA"),
    "MAD": (40.4936,  -3.5668,   "Madrid Barajas",          "ES"),
    "BCN": (41.2974,   2.0833,   "Barcelona El Prat",       "ES"),
    "FCO": (41.7999,  12.2462,   "Rome Fiumicino",          "IT"),
    "MXP": (45.6306,   8.7281,   "Milan Malpensa",          "IT"),
    "ZRH": (47.4647,   8.5492,   "Zurich",                  "CH"),
    "IST": (41.2608,  28.7418,   "Istanbul",                "TR"),
    "DOH": (25.2609,  51.6138,   "Doha Hamad",              "QA"),
    "BKK": (13.6811, 100.7470,   "Bangkok Suvarnabhumi",    "TH"),
    "KUL": ( 2.7456,  101.7099,  "Kuala Lumpur",            "MY"),
    "DEL": (28.5562,  77.1000,   "Delhi Indira Gandhi",     "IN"),
    "BOM": (19.0896,  72.8656,   "Mumbai",                  "IN"),
}

# Mapping préfixe IATA compagnie → hub d'origine probable
CARRIER_HUB = {
    "AF": "CDG", "KL": "AMS", "BA": "LHR", "LH": "FRA", "IB": "MAD",
    "EK": "DXB", "QR": "DOH", "EY": "AUH", "TK": "IST",
    "SQ": "SIN", "CX": "HKG", "NH": "HND", "JL": "NRT", "KE": "ICN",
    "OZ": "ICN", "CA": "PEK", "MU": "PVG", "CZ": "CAN",
    "UA": "ORD", "AA": "JFK", "DL": "JFK", "AC": "YYZ", "QF": "SYD",
    "FX": "MEM",
}


def guess_carrier(flight_number: str) -> str:
    prefix = "".join(c for c in flight_number if c.isalpha()).upper()
    return IATA_CARRIERS.get(prefix, prefix or "Unknown")


def resolve_airport(iata_code: str | None, fallback_iata: str | None = None) -> tuple | None:
    """Retourne (lat, lng, nom, iso) depuis un code IATA aéroport, ou None."""
    for code in [iata_code, fallback_iata]:
        if code and code.upper() in AIRPORTS:
            return AIRPORTS[code.upper()]
    return None


def get_or_create_demo_user():
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
    return user


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    flight_number: str,
    origin_iata: str | None = None,
    dest_iata: str | None = None,
    target_username: str | None = None,
    tracking_number: str | None = None,
    description: str | None = None,
    carrier: str | None = None,
    force: bool = False,
):
    flight_number = flight_number.strip().upper()
    prefix = "".join(c for c in flight_number if c.isalpha()).upper()

    # --- User ---
    if target_username:
        try:
            user = User.objects.get(username=target_username)
            print(f"[seed] User '{target_username}' trouvé (id={user.pk})")
        except User.DoesNotExist:
            print(f"[seed] ERREUR : user '{target_username}' introuvable. Annulation.")
            sys.exit(1)
    else:
        user = get_or_create_demo_user()

    # --- Valeurs par défaut ---
    tracking = tracking_number or f"DEMO-{flight_number}-001"
    desc     = description or f"Colis démo {flight_number}"
    car      = carrier or guess_carrier(flight_number)

    # --- Résolution aéroports ---
    # Priorité : argument CLI → hub connu de la compagnie → None
    carrier_hub = CARRIER_HUB.get(prefix)
    origin_data = resolve_airport(origin_iata, carrier_hub)
    dest_data   = resolve_airport(dest_iata)

    origin_country = origin_data[3] if origin_data else ""
    dest_country   = dest_data[3]   if dest_data   else ""

    # --- Gestion de l'existant ---
    existing = Parcel.objects.filter(tracking_number=tracking).first()
    if existing:
        if force:
            print(f"[seed] --force : suppression de '{tracking}'...")
            existing.delete()
        else:
            print(
                f"[seed] '{tracking}' existe déjà (owner={existing.owner.username}). "
                f"Utilisez --force pour le recréer."
            )
            sys.exit(0)

    # --- Création du colis ---
    parcel = Parcel.objects.create(
        tracking_number=tracking,
        carrier=car,
        description=desc,
        origin_country=origin_country,
        dest_country=dest_country,
        status=Parcel.Status.IN_TRANSIT,
        owner=user,
        flight_number=flight_number,
    )
    print(f"[seed] ✓ Colis '{tracking}' créé pour '{user.username}' (vol: {flight_number})")

    # --- Création des events (nécessaires pour l'arc SimEngine) ---
    now = timezone.now()

    if origin_data:
        o_lat, o_lng, o_name, _ = origin_data
        TrackingEvent.objects.create(
            parcel=parcel,
            timestamp=now - timedelta(hours=2),
            location=o_name,
            latitude=o_lat,
            longitude=o_lng,
            status="Départ",
            description=f"Vol {flight_number} départ",
            transport_mode=TrackingEvent.TransportMode.AIR,
        )
        print(f"[seed]   → event départ  : {o_name} ({o_lat}, {o_lng})")
    else:
        print(f"[seed]   ⚠ aéroport d'origine inconnu — passez --origin <IATA> pour former l'arc")

    if dest_data:
        d_lat, d_lng, d_name, _ = dest_data
        TrackingEvent.objects.create(
            parcel=parcel,
            timestamp=now + timedelta(hours=6),
            location=d_name,
            latitude=d_lat,
            longitude=d_lng,
            status="Arrivée estimée",
            description=f"Vol {flight_number} arrivée prévue",
            transport_mode=TrackingEvent.TransportMode.AIR,
        )
        print(f"[seed]   → event arrivée : {d_name} ({d_lat}, {d_lng})")
    else:
        print(f"[seed]   ⚠ aéroport de destination inconnu — passez --dest <IATA> pour former l'arc")

    # --- SimEngine (calcule estimated_departure / estimated_arrival) ---
    if origin_data and dest_data:
        compute_parcel_simulation(parcel)
        seg_count = parcel.events.filter(simulated=True).count()
        print(f"[seed]   → SimEngine OK ({seg_count} segments simulés)")
    else:
        print("[seed]   ⚠ SimEngine ignoré (il faut les 2 endpoints pour former un arc)")

    print("[seed] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed colis démo avec vol live — Orbi7rack")
    parser.add_argument("--flight",      required=True,  help="Numéro de vol IATA (ex: AF011)")
    parser.add_argument("--origin",      default=None,   help="Code IATA aéroport départ (ex: CDG)")
    parser.add_argument("--dest",        default=None,   help="Code IATA aéroport arrivée (ex: JFK)")
    parser.add_argument("--username",    default=None,   help="Username du compte cible (défaut: 'demo')")
    parser.add_argument("--tracking",    default=None,   help="Numéro de tracking custom")
    parser.add_argument("--description", default=None,   help="Description du colis")
    parser.add_argument("--carrier",     default=None,   help="Nom du transporteur")
    parser.add_argument("--force",       action="store_true", help="Supprime et recrée si le tracking existe déjà")
    args = parser.parse_args()

    run(
        flight_number=args.flight,
        origin_iata=args.origin,
        dest_iata=args.dest,
        target_username=args.username,
        tracking_number=args.tracking,
        description=args.description,
        carrier=args.carrier,
        force=args.force,
    )
