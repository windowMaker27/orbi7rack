"""
seed_demo.py — Crée un colis de démo lié à un vol live.

Crée 2 events (départ + arrivée estimée) géocodés depuis les aéroports
IATA du vol, ce qui permet au SimulationEngine de former un arc.

Résolution automatique origin/dest :
  1. Arguments CLI --origin / --dest
  2. Table FLIGHT_ROUTES (vols fréquents connus)
  3. CARRIER_HUB (hub de la compagnie pour l'origine)

Usage (depuis /backend) :
  docker compose exec backend python scripts/seed_demo.py --flight AF011
  docker compose exec backend python scripts/seed_demo.py --flight DL95 --username admin --force
  docker compose exec backend python scripts/seed_demo.py --flight EK073 --origin DXB --dest CDG

Arguments :
  --flight      OBLIGATOIRE. Numéro de vol IATA (ex: AF011, DL95).
  --origin      Code IATA aéroport départ (ex: CDG). Optionnel si vol connu.
  --dest        Code IATA aéroport arrivée (ex: JFK). Optionnel si vol connu.
  --username    Attache le colis à un user existant (défaut: user 'demo').
  --tracking    Numéro de tracking custom (défaut: DEMO-<FLIGHT>-001).
  --description Description du colis.
  --carrier     Transporteur (défaut: extrait du préfixe IATA).
  --force       Supprime et recrée si le tracking existe déjà.
"""
import os
import sys
import argparse
import django
from pathlib import Path

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
    "AF": "Air France",      "UA": "United Airlines",  "AA": "American Airlines",
    "BA": "British Airways", "LH": "Lufthansa",        "EK": "Emirates",
    "QR": "Qatar Airways",   "DL": "Delta Air Lines",  "KL": "KLM",
    "IB": "Iberia",          "TK": "Turkish Airlines", "SQ": "Singapore Airlines",
    "CX": "Cathay Pacific",  "NH": "ANA",              "JL": "Japan Airlines",
    "CA": "Air China",       "MU": "China Eastern",    "CZ": "China Southern",
    "KE": "Korean Air",      "OZ": "Asiana Airlines",  "AC": "Air Canada",
    "QF": "Qantas",          "EY": "Etihad",           "FX": "FedEx",
    "LX": "Swiss",           "OS": "Austrian",         "SK": "SAS",
    "AY": "Finnair",         "AZ": "ITA Airways",
}

# (lat, lng, nom affiché, iso_country)
AIRPORTS = {
    # France
    "CDG": (49.0097,    2.5479,   "Paris Charles de Gaulle",  "FR"),
    "ORY": (48.7233,    2.3794,   "Paris Orly",               "FR"),
    "LYS": (45.7216,    5.0810,   "Lyon Saint-Exupéry",       "FR"),
    "MRS": (43.4365,    5.2150,   "Marseille Provence",        "FR"),
    "NCE": (43.6584,    7.2159,   "Nice Côte d'Azur",          "FR"),
    # Europe
    "LHR": (51.4700,   -0.4543,   "London Heathrow",           "GB"),
    "LGW": (51.1537,   -0.1821,   "London Gatwick",            "GB"),
    "FRA": (50.0379,    8.5622,   "Frankfurt",                 "DE"),
    "MUC": (48.3537,   11.7750,   "Munich",                    "DE"),
    "TXL": (52.5597,   13.2877,   "Berlin Tegel",              "DE"),
    "BER": (52.3667,   13.5033,   "Berlin Brandenburg",        "DE"),
    "LEJ": (51.4239,   12.2364,   "Leipzig",                   "DE"),
    "AMS": (52.3086,    4.7639,   "Amsterdam Schiphol",        "NL"),
    "BRU": (50.9010,    4.4844,   "Brussels",                  "BE"),
    "ZRH": (47.4647,    8.5492,   "Zurich",                    "CH"),
    "GVA": (46.2381,    6.1089,   "Geneva",                    "CH"),
    "VIE": (48.1103,   16.5697,   "Vienna",                    "AT"),
    "MAD": (40.4936,   -3.5668,   "Madrid Barajas",            "ES"),
    "BCN": (41.2974,    2.0833,   "Barcelona El Prat",         "ES"),
    "FCO": (41.7999,   12.2462,   "Rome Fiumicino",            "IT"),
    "MXP": (45.6306,    8.7281,   "Milan Malpensa",            "IT"),
    "CPH": (55.6180,   12.6561,   "Copenhagen",                "DK"),
    "ARN": (59.6519,   17.9186,   "Stockholm Arlanda",         "SE"),
    "HEL": (60.3172,   24.9633,   "Helsinki",                  "FI"),
    "OSL": (60.1939,   11.1004,   "Oslo Gardermoen",           "NO"),
    "IST": (41.2608,   28.7418,   "Istanbul",                  "TR"),
    "SVO": (55.9726,   37.4146,   "Moscow Sheremetyevo",       "RU"),
    "WAW": (52.1657,   20.9671,   "Warsaw Chopin",             "PL"),
    "STR": (48.6899,    9.2220,   "Strasbourg",                "FR"),
    # Moyen-Orient
    "DXB": (25.2532,   55.3657,   "Dubai",                     "AE"),
    "AUH": (24.4330,   54.6511,   "Abu Dhabi",                 "AE"),
    "DOH": (25.2609,   51.6138,   "Doha Hamad",                "QA"),
    "RUH": (24.9576,   46.6988,   "Riyadh",                    "SA"),
    # Asie
    "SIN": ( 1.3644,  103.9915,   "Singapore Changi",          "SG"),
    "HKG": (22.3080,  113.9185,   "Hong Kong",                 "HK"),
    "NRT": (35.7647,  140.3864,   "Tokyo Narita",              "JP"),
    "HND": (35.5494,  139.7798,   "Tokyo Haneda",              "JP"),
    "KIX": (34.4347,  135.2440,   "Osaka Kansai",              "JP"),
    "ICN": (37.4602,  126.4407,   "Seoul Incheon",             "KR"),
    "PVG": (31.1434,  121.8052,   "Shanghai Pudong",           "CN"),
    "PEK": (40.0799,  116.6031,   "Beijing Capital",           "CN"),
    "PKX": (39.5090,  116.4100,   "Beijing Daxing",            "CN"),
    "SZX": (22.6395,  113.8145,   "Shenzhen",                  "CN"),
    "CAN": (23.3924,  113.2988,   "Guangzhou",                 "CN"),
    "CTU": (30.5785,  103.9473,   "Chengdu",                   "CN"),
    "BKK": (13.6811,  100.7470,   "Bangkok Suvarnabhumi",      "TH"),
    "KUL": ( 2.7456,  101.7099,   "Kuala Lumpur",              "MY"),
    "DEL": (28.5562,   77.1000,   "Delhi Indira Gandhi",       "IN"),
    "BOM": (19.0896,   72.8656,   "Mumbai",                    "IN"),
    "BLR": (13.1986,   77.7066,   "Bangalore",                 "IN"),
    # Amérique du Nord
    "JFK": (40.6413,  -73.7781,   "New York JFK",              "US"),
    "EWR": (40.6895,  -74.1745,   "New York Newark",           "US"),
    "LAX": (33.9425, -118.4081,   "Los Angeles",               "US"),
    "ORD": (41.9742,  -87.9073,   "Chicago O'Hare",            "US"),
    "ATL": (33.6407,  -84.4277,   "Atlanta",                   "US"),
    "DTW": (42.2124,  -83.3534,   "Detroit Metro",             "US"),
    "MIA": (25.7959,  -80.2870,   "Miami",                     "US"),
    "SFO": (37.6213, -122.3790,   "San Francisco",             "US"),
    "SEA": (47.4502, -122.3088,   "Seattle",                   "US"),
    "BOS": (42.3656,  -71.0096,   "Boston",                    "US"),
    "IAD": (38.9531,  -77.4565,   "Washington Dulles",         "US"),
    "YYZ": (43.6777,  -79.6248,   "Toronto Pearson",           "CA"),
    "YUL": (45.4706,  -73.7408,   "Montreal",                  "CA"),
    "MEX": (19.4363,  -99.0721,   "Mexico City",               "MX"),
    # Amérique du Sud / Océanie / Afrique
    "GRU": (-23.4356, -46.4731,   "São Paulo Guarulhos",       "BR"),
    "EZE": (-34.8222, -58.5358,   "Buenos Aires Ezeiza",       "AR"),
    "SCL": (-33.3930, -70.7858,   "Santiago",                  "CL"),
    "SYD": (-33.9399, 151.1753,   "Sydney",                    "AU"),
    "MEL": (-37.6733, 144.8430,   "Melbourne",                 "AU"),
    "JNB": (-26.1392,  28.2460,   "Johannesburg",              "ZA"),
    "CAI": (30.1219,   31.4056,   "Cairo",                     "EG"),
    "CMN": (33.3675,   -7.5898,   "Casablanca Mohammed V",     "MA"),
}

# Hub principal par préfixe IATA compagnie (fallback origine)
CARRIER_HUB = {
    "AF": "CDG", "KL": "AMS", "BA": "LHR", "LH": "FRA", "IB": "MAD",
    "EK": "DXB", "QR": "DOH", "EY": "AUH", "TK": "IST",
    "SQ": "SIN", "CX": "HKG", "NH": "HND", "JL": "NRT", "KE": "ICN",
    "OZ": "ICN", "CA": "PEK", "MU": "PVG", "CZ": "CAN",
    "UA": "ORD", "AA": "JFK", "DL": "ATL", "AC": "YYZ", "QF": "SYD",
    "LX": "ZRH", "OS": "VIE", "SK": "ARN", "AY": "HEL", "AZ": "FCO",
}

# Routes connues par numéro de vol exact : (origin_IATA, dest_IATA)
FLIGHT_ROUTES = {
    # Delta
    "DL95":  ("CDG", "DTW"), "DL96":  ("DTW", "CDG"),  # Paris ↔ Detroit
    "DL180": ("CDG", "JFK"), "DL181": ("JFK", "CDG"),
    "DL400": ("ATL", "LHR"), "DL401": ("LHR", "ATL"),
    # Air France
    "AF011": ("CDG", "JFK"), "AF012": ("JFK", "CDG"),
    "AF066": ("CDG", "LAX"), "AF068": ("LAX", "CDG"),
    "AF160": ("CDG", "NRT"), "AF264": ("CDG", "PVG"),
    "AF447": ("CDG", "GRU"),
    # United
    "UA57":  ("EWR", "LHR"), "UA58":  ("LHR", "EWR"),
    "UA984": ("SFO", "NRT"),
    # Singapore Airlines
    "SQ335": ("SIN", "LAX"), "SQ336": ("LAX", "SIN"),
    "SQ317": ("SIN", "CDG"), "SQ318": ("CDG", "SIN"),
    # Emirates
    "EK073": ("DXB", "CDG"), "EK074": ("CDG", "DXB"),
    "EK201": ("DXB", "JFK"), "EK202": ("JFK", "DXB"),
    # British Airways
    "BA303": ("LHR", "JFK"), "BA178": ("LHR", "HKG"),
    # Lufthansa
    "LH400": ("FRA", "JFK"), "LH401": ("JFK", "FRA"),
    "LH716": ("FRA", "NRT"),
    # KLM
    "KL861": ("AMS", "NRT"), "KL862": ("NRT", "AMS"),
    # Korean Air
    "KE901": ("ICN", "CDG"), "KE902": ("CDG", "ICN"),
    # Qatar
    "QR006": ("DOH", "CDG"), "QR007": ("CDG", "DOH"),
    # FedEx
    "FX5025": ("SZX", "CDG"),
}


def guess_carrier(flight_number: str) -> str:
    prefix = "".join(c for c in flight_number if c.isalpha()).upper()
    return IATA_CARRIERS.get(prefix, prefix or "Unknown")


def resolve_route(flight_number: str, origin_arg: str | None, dest_arg: str | None, prefix: str):
    """
    Résout (origin_data, dest_data) selon la priorité :
      1. CLI args
      2. FLIGHT_ROUTES (numéro exact)
      3. CARRIER_HUB (origine seulement)
    """
    route = FLIGHT_ROUTES.get(flight_number)
    resolved_origin = origin_arg or (route[0] if route else None) or CARRIER_HUB.get(prefix)
    resolved_dest   = dest_arg   or (route[1] if route else None)

    origin_data = AIRPORTS.get(resolved_origin.upper()) if resolved_origin else None
    dest_data   = AIRPORTS.get(resolved_dest.upper())   if resolved_dest   else None
    return origin_data, dest_data


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

    if target_username:
        try:
            user = User.objects.get(username=target_username)
            print(f"[seed] User '{target_username}' trouvé (id={user.pk})")
        except User.DoesNotExist:
            print(f"[seed] ERREUR : user '{target_username}' introuvable. Annulation.")
            sys.exit(1)
    else:
        user = get_or_create_demo_user()

    tracking = tracking_number or f"DEMO-{flight_number}-001"
    desc     = description or f"Colis démo {flight_number}"
    car      = carrier or guess_carrier(flight_number)

    origin_data, dest_data = resolve_route(flight_number, origin_iata, dest_iata, prefix)
    origin_country = origin_data[3] if origin_data else ""
    dest_country   = dest_data[3]   if dest_data   else ""

    existing = Parcel.objects.filter(tracking_number=tracking).first()
    if existing:
        if force:
            print(f"[seed] --force : suppression de '{tracking}'...")
            existing.delete()
        else:
            print(f"[seed] '{tracking}' existe déjà (owner={existing.owner.username}). Utilisez --force pour recréer.")
            sys.exit(0)

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
        print(f"[seed]   ⚠ origine inconnue — passez --origin <IATA>")

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
        print(f"[seed]   ⚠ destination inconnue — passez --dest <IATA>")

    if origin_data and dest_data:
        compute_parcel_simulation(parcel)
        seg_count = parcel.events.filter(simulated=True).count()
        print(f"[seed]   → SimEngine OK ({seg_count} segments simulés)")
    else:
        print("[seed]   ⚠ SimEngine ignoré (il faut les 2 endpoints)")

    print("[seed] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed colis démo avec vol live — Orbi7rack")
    parser.add_argument("--flight",      required=True)
    parser.add_argument("--origin",      default=None, help="Code IATA aéroport départ (ex: CDG)")
    parser.add_argument("--dest",        default=None, help="Code IATA aéroport arrivée (ex: JFK)")
    parser.add_argument("--username",    default=None)
    parser.add_argument("--tracking",    default=None)
    parser.add_argument("--description", default=None)
    parser.add_argument("--carrier",     default=None)
    parser.add_argument("--force",       action="store_true")
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
