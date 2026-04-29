"""
Usage:
  python manage.py seed_demo
  python manage.py seed_demo AF011 BA306
  python manage.py seed_demo AF011:CDG:JFK BA306:LHR:CDG
  python manage.py seed_demo --user admin --reset AF011

Format des tokens :
  - "AF011"          → lookup AviationStack API puis saisie manuelle si échec
  - "AF011:CDG:JFK"  → bypass direct (pas d'API call)

Variables d'environnement :
  AVIATIONSTACK_API_KEY   — clé API AviationStack
  AVIATIONSTACK_BASE_URL  — défaut: http://api.aviationstack.com/v1
"""
import requests
from decouple import config as decouple_config
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tracking.models import Parcel, TrackingEvent

AVIATION_API_KEY  = decouple_config("AVIATIONSTACK_API_KEY", default="")
AVIATION_BASE_URL = decouple_config("AVIATIONSTACK_BASE_URL", default="http://api.aviationstack.com/v1")

IATA_META: dict[str, dict] = {
    "CDG": {"country": "FR", "lat": 49.0097,  "lng":   2.5479, "name": "Paris Charles de Gaulle"},
    "ORY": {"country": "FR", "lat": 48.7262,  "lng":   2.3652, "name": "Paris Orly"},
    "LHR": {"country": "GB", "lat": 51.4775,  "lng":  -0.4614, "name": "London Heathrow"},
    "LGW": {"country": "GB", "lat": 51.1537,  "lng":  -0.1821, "name": "London Gatwick"},
    "MAN": {"country": "GB", "lat": 53.3537,  "lng":  -2.2750, "name": "Manchester Intl"},
    "JFK": {"country": "US", "lat": 40.6413,  "lng": -73.7781, "name": "New York JFK"},
    "EWR": {"country": "US", "lat": 40.6895,  "lng": -74.1745, "name": "New York Newark"},
    "LGA": {"country": "US", "lat": 40.7772,  "lng": -73.8726, "name": "New York LaGuardia"},
    "LAX": {"country": "US", "lat": 33.9425,  "lng":-118.4081, "name": "Los Angeles"},
    "SFO": {"country": "US", "lat": 37.6213,  "lng":-122.3790, "name": "San Francisco"},
    "ORD": {"country": "US", "lat": 41.9742,  "lng": -87.9073, "name": "Chicago O'Hare"},
    "ATL": {"country": "US", "lat": 33.6407,  "lng": -84.4277, "name": "Atlanta Hartsfield"},
    "DFW": {"country": "US", "lat": 32.8998,  "lng": -97.0403, "name": "Dallas Fort Worth"},
    "MIA": {"country": "US", "lat": 25.7959,  "lng": -80.2870, "name": "Miami Intl"},
    "SEA": {"country": "US", "lat": 47.4502,  "lng":-122.3088, "name": "Seattle-Tacoma"},
    "BOS": {"country": "US", "lat": 42.3656,  "lng": -71.0096, "name": "Boston Logan"},
    "IAD": {"country": "US", "lat": 38.9531,  "lng": -77.4565, "name": "Washington Dulles"},
    "IAH": {"country": "US", "lat": 29.9902,  "lng": -95.3368, "name": "Houston Bush Intercontinental"},
    "DXB": {"country": "AE", "lat": 25.2532,  "lng":  55.3657, "name": "Dubai Intl"},
    "SIN": {"country": "SG", "lat":  1.3644,  "lng": 103.9915, "name": "Singapore Changi"},
    "HKG": {"country": "HK", "lat": 22.3080,  "lng": 113.9185, "name": "Hong Kong Intl"},
    "PEK": {"country": "CN", "lat": 40.0799,  "lng": 116.6031, "name": "Beijing Capital"},
    "PKX": {"country": "CN", "lat": 39.5097,  "lng": 116.4105, "name": "Beijing Daxing"},
    "PVG": {"country": "CN", "lat": 31.1443,  "lng": 121.8083, "name": "Shanghai Pudong"},
    "SHA": {"country": "CN", "lat": 31.1979,  "lng": 121.3362, "name": "Shanghai Hongqiao"},
    "CAN": {"country": "CN", "lat": 23.3924,  "lng": 113.2988, "name": "Guangzhou Baiyun"},
    "ICN": {"country": "KR", "lat": 37.4602,  "lng": 126.4407, "name": "Seoul Incheon"},
    "NRT": {"country": "JP", "lat": 35.7647,  "lng": 140.3864, "name": "Tokyo Narita"},
    "HND": {"country": "JP", "lat": 35.5494,  "lng": 139.7798, "name": "Tokyo Haneda"},
    "KIX": {"country": "JP", "lat": 34.4347,  "lng": 135.2440, "name": "Osaka Kansai"},
    "FRA": {"country": "DE", "lat": 50.0379,  "lng":   8.5622, "name": "Frankfurt Intl"},
    "MUC": {"country": "DE", "lat": 48.3538,  "lng":  11.7861, "name": "Munich Intl"},
    "AMS": {"country": "NL", "lat": 52.3086,  "lng":   4.7639, "name": "Amsterdam Schiphol"},
    "MAD": {"country": "ES", "lat": 40.4983,  "lng":  -3.5676, "name": "Madrid Barajas"},
    "BCN": {"country": "ES", "lat": 41.2971,  "lng":   2.0785, "name": "Barcelona El Prat"},
    "FCO": {"country": "IT", "lat": 41.8003,  "lng":  12.2389, "name": "Rome Fiumicino"},
    "MXP": {"country": "IT", "lat": 45.6306,  "lng":   8.7231, "name": "Milan Malpensa"},
    "ZRH": {"country": "CH", "lat": 47.4647,  "lng":   8.5492, "name": "Zurich"},
    "BRU": {"country": "BE", "lat": 50.9010,  "lng":   4.4844, "name": "Brussels Zaventem"},
    "GRU": {"country": "BR", "lat": -23.4356, "lng": -46.4731, "name": "São Paulo Guarulhos"},
    "EZE": {"country": "AR", "lat": -34.8222, "lng": -58.5358, "name": "Buenos Aires Ezeiza"},
    "BOG": {"country": "CO", "lat":   4.7016,  "lng": -74.1469, "name": "Bogotá El Dorado"},
    "MEX": {"country": "MX", "lat":  19.4363,  "lng": -99.0721, "name": "Mexico City Intl"},
    "YYZ": {"country": "CA", "lat":  43.6777,  "lng": -79.6248, "name": "Toronto Pearson"},
    "YUL": {"country": "CA", "lat":  45.4706,  "lng": -73.7408, "name": "Montreal Trudeau"},
    "YVR": {"country": "CA", "lat":  49.1967,  "lng":-123.1815, "name": "Vancouver Intl"},
    "SYD": {"country": "AU", "lat": -33.9461, "lng": 151.1772, "name": "Sydney Kingsford Smith"},
    "MEL": {"country": "AU", "lat": -37.6690, "lng": 144.8410, "name": "Melbourne Tullamarine"},
    "CPT": {"country": "ZA", "lat": -33.9715, "lng":  18.6021, "name": "Cape Town Intl"},
    "JNB": {"country": "ZA", "lat": -26.1367, "lng":  28.2411, "name": "Johannesburg OR Tambo"},
    "CAI": {"country": "EG", "lat":  30.1219, "lng":  31.4056, "name": "Cairo Intl"},
    "IST": {"country": "TR", "lat":  41.2753, "lng":  28.7519, "name": "Istanbul Airport"},
    "SAW": {"country": "TR", "lat":  40.8985,  "lng":  29.3092, "name": "Istanbul Sabiha Gökçen"},
    "DOH": {"country": "QA", "lat":  25.2731, "lng":  51.6081, "name": "Doha Hamad Intl"},
    "AUH": {"country": "AE", "lat":  24.4330, "lng":  54.6511, "name": "Abu Dhabi Intl"},
    "BKK": {"country": "TH", "lat":  13.6900, "lng": 100.7501, "name": "Bangkok Suvarnabhumi"},
    "KUL": {"country": "MY", "lat":   2.7456, "lng": 101.7099, "name": "Kuala Lumpur Intl"},
    "MNL": {"country": "PH", "lat":  14.5086, "lng": 121.0197, "name": "Manila Ninoy Aquino"},
    "CGK": {"country": "ID", "lat":  -6.1256, "lng": 106.6559, "name": "Jakarta Soekarno-Hatta"},
    "DEL": {"country": "IN", "lat":  28.5562, "lng":  77.1000, "name": "Delhi Indira Gandhi"},
    "BOM": {"country": "IN", "lat":  19.0896, "lng":  72.8656, "name": "Mumbai Chhatrapati Shivaji"},
    "BLR": {"country": "IN", "lat":  13.1986, "lng":  77.7066, "name": "Bangalore Kempegowda"},
    # DOM-TOM / Outre-mer français
    "RUN": {"country": "RE", "lat": -20.8872, "lng":  55.5136, "name": "La Réunion Roland Garros"},
    "FDF": {"country": "MQ", "lat":  14.5910, "lng": -61.0032, "name": "Fort-de-France Aimé Césaire (Martinique)"},
    "PTP": {"country": "GP", "lat":  16.2653, "lng": -61.5272, "name": "Pointe-à-Pitre Guadeloupe"},
    "CAY": {"country": "GF", "lat":   4.8198, "lng": -52.3608, "name": "Cayenne Félix Eboué (Guyane)"},
    "DZA": {"country": "YT", "lat": -12.8047, "lng":  45.2811, "name": "Mayotte Dzaoudzi-Pamandzi"},
    "NOU": {"country": "NC", "lat": -22.0146, "lng": 166.2129, "name": "Nouméa La Tontouta (Nouvelle-Calédonie)"},
    "PPT": {"country": "PF", "lat": -17.5534, "lng":-149.6067, "name": "Papeete Faa'a (Polynésie française)"},
    # Reste Europe
    "VIE": {"country": "AT", "lat":  48.1103, "lng":  16.5697, "name": "Vienna Intl"},
    "LIS": {"country": "PT", "lat":  38.7742, "lng":  -9.1342, "name": "Lisbon Humberto Delgado"},
    "ARN": {"country": "SE", "lat":  59.6519, "lng":  17.9186, "name": "Stockholm Arlanda"},
    "CPH": {"country": "DK", "lat":  55.6180, "lng":  12.6508, "name": "Copenhagen Kastrup"},
    "HEL": {"country": "FI", "lat":  60.3172, "lng":  24.9633, "name": "Helsinki Vantaa"},
    "OSL": {"country": "NO", "lat":  60.1939, "lng":  11.1004, "name": "Oslo Gardermoen"},
    "WAW": {"country": "PL", "lat":  52.1657, "lng":  20.9671, "name": "Warsaw Chopin"},
    "PRG": {"country": "CZ", "lat":  50.1008, "lng":  14.2600, "name": "Prague Václav Havel"},
    "BUD": {"country": "HU", "lat":  47.4298, "lng":  19.2611, "name": "Budapest Ferenc Liszt"},
    "ATH": {"country": "GR", "lat":  37.9364, "lng":  23.9444, "name": "Athens Eleftherios Venizelos"},
    "NBO": {"country": "KE", "lat":  -1.3192, "lng":  36.9275, "name": "Nairobi Jomo Kenyatta"},
    "LOS": {"country": "NG", "lat":   6.5774, "lng":   3.3212, "name": "Lagos Murtala Muhammed"},
    "ADD": {"country": "ET", "lat":   8.9779, "lng":  38.7993, "name": "Addis Ababa Bole"},
    "ACC": {"country": "GH", "lat":   5.6052, "lng":  -0.1668, "name": "Accra Kotoka"},
    "GVA": {"country": "CH", "lat":  46.2380, "lng":   6.1089, "name": "Geneva Cointrin"},
    "DUS": {"country": "DE", "lat":  51.2895, "lng":   6.7668, "name": "Düsseldorf Intl"},
    "HAM": {"country": "DE", "lat":  53.6304, "lng":  10.0060, "name": "Hamburg Intl"},
    "NCE": {"country": "FR", "lat":  43.6584, "lng":   7.2159, "name": "Nice Côte d'Azur"},
    "MRS": {"country": "FR", "lat":  43.4393, "lng":   5.2214, "name": "Marseille Provence"},
    "LYS": {"country": "FR", "lat":  45.7256, "lng":   5.0811, "name": "Lyon Saint-Exupéry"},
}


def iata_meta(code: str) -> dict | None:
    return IATA_META.get(code.upper())


def lookup_flight_api(flight_number: str) -> dict | None:
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
            "origin_iata":   f["departure"]["iata"],
            "dest_iata":     f["arrival"]["iata"],
            "airline":       f["airline"]["name"],
            "flight_status": f.get("flight_status", "active"),
        }
    except Exception:
        return None


class Command(BaseCommand):
    help = "Crée des colis démo avec différents statuts (camion FR, pending, livraison, livré)"

    def add_arguments(self, parser):
        parser.add_argument(
            "flights",
            nargs="*",
            help="Tokens vol : 'AF011' ou 'AF011:CDG:JFK'. Si vide, utilise les colis hardcodés.",
        )
        parser.add_argument(
            "--user", default="",
            help="Username du propriétaire (défaut: premier superuser)",
        )
        parser.add_argument(
            "--reset", action="store_true",
            help="Supprime les colis DEMO-* existants avant de recréer",
        )

    def _resolve_flight(self, token: str) -> dict | None:
        parts = token.split(":")
        flight_number = parts[0].upper()

        if len(parts) == 3:
            return {
                "flight_number": flight_number,
                "origin_iata":   parts[1].upper(),
                "dest_iata":     parts[2].upper(),
                "airline":       "",
            }

        self.stdout.write(f"[INFO] Lookup API pour {flight_number}…")
        if not AVIATION_API_KEY:
            self.stderr.write(self.style.WARNING(
                f"  ✗ AVIATIONSTACK_API_KEY absent du .env. Utilisez 'FLXX:ORIG:DEST' pour bypass."
            ))
            return None

        result = lookup_flight_api(flight_number)
        if result:
            self.stdout.write(
                f"  ✓ {flight_number}: {result['origin_iata']} → {result['dest_iata']} ({result['airline']})"
            )
            return {"flight_number": flight_number, **result}

        self.stderr.write(self.style.WARNING(
            f"  ✗ Vol {flight_number} introuvable via API. Utilisez 'FLXX:ORIG:DEST' pour bypass."
        ))
        return None

    def _create_parcel(self, owner, flight: dict, now) -> None:
        """
        Crée un colis in_transit lié à un vol.
        - Si l'IATA est dans IATA_META : event avec coords précises
        - Si l'IATA est INCONNU       : event créé quand même (sans coords) — pas de drop silencieux
        """
        fn   = flight["flight_number"]
        orig = iata_meta(flight["origin_iata"])
        dest = iata_meta(flight["dest_iata"])

        origin_country = (orig or {}).get("country", flight["origin_iata"])
        dest_country   = (dest or {}).get("country", flight["dest_iata"])
        origin_name    = (orig or {}).get("name", flight["origin_iata"])
        dest_name      = (dest or {}).get("name", flight["dest_iata"])

        if not orig:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ IATA '{flight['origin_iata']}' inconnu — event départ sans coords")
            )
        if not dest:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ IATA '{flight['dest_iata']}' inconnu — event arrivée sans coords")
            )

        tracking_number = f"DEMO-LIVE-{fn}"
        Parcel.objects.filter(tracking_number=tracking_number).delete()

        parcel = Parcel.objects.create(
            owner=owner,
            tracking_number=tracking_number,
            carrier=flight.get("airline") or "Unknown Airline",
            description=f"Colis démo lié au vol {fn} [LIVE]",
            origin_country=origin_country,
            dest_country=dest_country,
            status="in_transit",
            flight_number=fn,
            last_synced_at=now,
        )

        # Toujours 2 events — avec coords si IATA connu, sans coords sinon
        events = [
            TrackingEvent(
                parcel=parcel,
                timestamp=now - timezone.timedelta(hours=2),
                location=origin_name,
                latitude=orig["lat"] if orig else None,
                longitude=orig["lng"] if orig else None,
                status="in_transit",
                description=f"Départ de {origin_name} sur le vol {fn}",
            ),
            TrackingEvent(
                parcel=parcel,
                timestamp=now + timezone.timedelta(hours=8),
                location=dest_name,
                latitude=dest["lat"] if dest else None,
                longitude=dest["lng"] if dest else None,
                status="in_transit",
                description=f"Arrivée prévue à {dest_name}",
            ),
        ]

        TrackingEvent.objects.bulk_create(events)
        n_geo = sum(1 for e in events if e.latitude is not None)
        self.stdout.write(self.style.SUCCESS(
            f"✅ {tracking_number} — {origin_name} ({origin_country}) → {dest_name} ({dest_country})"
            f" — vol {fn} (2 events, {n_geo} géocodé(s))"
        ))

    def _create_static_parcel(
        self,
        owner,
        tracking_number: str,
        carrier: str,
        description: str,
        origin_country: str,
        dest_country: str,
        status: str,
        events_data: list[dict],
        now,
        last_live_lat: float | None = None,
        last_live_lng: float | None = None,
        last_live_at=None,
    ) -> None:
        """Crée un colis statique (pas de vol live) avec ses événements."""
        Parcel.objects.filter(tracking_number=tracking_number).delete()
        parcel = Parcel.objects.create(
            owner=owner,
            tracking_number=tracking_number,
            carrier=carrier,
            description=description,
            origin_country=origin_country,
            dest_country=dest_country,
            status=status,
            last_synced_at=now,
            last_live_lat=last_live_lat,
            last_live_lng=last_live_lng,
            last_live_at=last_live_at,
        )
        events = [
            TrackingEvent(
                parcel=parcel,
                timestamp=e["timestamp"],
                location=e["location"],
                latitude=e.get("lat"),
                longitude=e.get("lng"),
                status=e["status"],
                description=e["description"],
            )
            for e in events_data
        ]
        TrackingEvent.objects.bulk_create(events)
        self.stdout.write(self.style.SUCCESS(
            f"✅ {tracking_number} [{status}] — {description} ({len(events)} events)"
        ))

    def _seed_hardcoded(self, owner, now) -> None:
        """
        4 scénarios de démo fixés — toujours les mêmes pour une présentation reproductible.

        1. DEMO-TRUCK-FR      : out_for_delivery — camion en route sur Paris
        2. DEMO-PENDING-CN    : pending — colis bloqué dans un centre de tri à Shanghai
        3. DEMO-OFD-JP        : out_for_delivery — livraison express Tokyo
        4. DEMO-DELIVERED-US  : delivered — colis livré à Manhattan
        """

        # ------------------------------------------------------------
        # 1. Camion en livraison — Paris, France
        # ------------------------------------------------------------
        self._create_static_parcel(
            owner=owner,
            tracking_number="DEMO-TRUCK-FR",
            carrier="Chronopost",
            description="Composants électroniques — livraison du jour à Paris",
            origin_country="CN",
            dest_country="FR",
            status="out_for_delivery",
            events_data=[
                {
                    "timestamp": now - timezone.timedelta(days=5),
                    "location": "Shanghai Pudong — entrepôt expéditeur",
                    "lat": 31.1443, "lng": 121.8083,
                    "status": "in_transit",
                    "description": "Colis pris en charge par DHL Express Shanghai",
                },
                {
                    "timestamp": now - timezone.timedelta(days=4),
                    "location": "Paris CDG — plateforme aérienne",
                    "lat": 49.0097, "lng": 2.5479,
                    "status": "in_transit",
                    "description": "Arrivée en France, passage en douane validé",
                },
                {
                    "timestamp": now - timezone.timedelta(hours=14),
                    "location": "Chronopost Roissy — hub régional",
                    "lat": 49.0097, "lng": 2.5479,
                    "status": "out_for_delivery",
                    "description": "Colis trié et assigné au livreur",
                },
                {
                    "timestamp": now - timezone.timedelta(hours=1, minutes=20),
                    "location": "Villepinte (93) — en route",
                    "lat": 48.9667, "lng": 2.5333,
                    "status": "out_for_delivery",
                    "description": "Camion en route — livraison prévue avant 13h",
                },
            ],
            now=now,
        )

        # ------------------------------------------------------------
        # 2. Pending — bloqué dans un centre de tri, Shanghai
        # ------------------------------------------------------------
        self._create_static_parcel(
            owner=owner,
            tracking_number="DEMO-PENDING-CN",
            carrier="China Post EMS",
            description="Textile — en attente de libération douanière",
            origin_country="CN",
            dest_country="FR",
            status="pending",
            events_data=[
                {
                    "timestamp": now - timezone.timedelta(days=3),
                    "location": "Guangzhou — entrepôt vendeur",
                    "lat": 23.3924, "lng": 113.2988,
                    "status": "pending",
                    "description": "Commande validée, préparation en cours",
                },
                {
                    "timestamp": now - timezone.timedelta(days=2),
                    "location": "Centre de tri Shanghai — Pudong",
                    "lat": 31.1443, "lng": 121.8083,
                    "status": "pending",
                    "description": "Colis reçu au centre de tri, en attente de contrôle export",
                },
                {
                    "timestamp": now - timezone.timedelta(hours=6),
                    "location": "Centre de tri Shanghai — Pudong",
                    "lat": 31.1443, "lng": 121.8083,
                    "status": "pending",
                    "description": "Inspection douanière requise — délai estimé 24-48h",
                },
            ],
            now=now,
        )

        # ------------------------------------------------------------
        # 3. Out for delivery — livraison express Tokyo, Japon
        # ------------------------------------------------------------
        self._create_static_parcel(
            owner=owner,
            tracking_number="DEMO-OFD-JP",
            carrier="Yamato Transport",
            description="Montre de luxe — livraison express 2h Tokyo",
            origin_country="FR",
            dest_country="JP",
            status="out_for_delivery",
            events_data=[
                {
                    "timestamp": now - timezone.timedelta(days=2),
                    "location": "Paris CDG — aéroport",
                    "lat": 49.0097, "lng": 2.5479,
                    "status": "in_transit",
                    "description": "Expédié depuis Paris sur vol cargo Air France",
                },
                {
                    "timestamp": now - timezone.timedelta(hours=10),
                    "location": "Tokyo Narita — fret aérien",
                    "lat": 35.7647, "lng": 140.3864,
                    "status": "in_transit",
                    "description": "Arrivée au Japon, dédouanement terminé",
                },
                {
                    "timestamp": now - timezone.timedelta(hours=3),
                    "location": "Yamato — dépôt Shinjuku",
                    "lat": 35.6938, "lng": 139.7034,
                    "status": "out_for_delivery",
                    "description": "En cours de livraison — livreur en route",
                },
                {
                    "timestamp": now - timezone.timedelta(minutes=30),
                    "location": "Shinjuku, Tokyo",
                    "lat": 35.6895, "lng": 139.6917,
                    "status": "out_for_delivery",
                    "description": "Livreur à proximité — tentative de livraison imminente",
                },
            ],
            now=now,
        )

        # ------------------------------------------------------------
        # 4. Delivered — livré à Manhattan, New York
        # ------------------------------------------------------------
        delivered_lat = 40.7549
        delivered_lng = -73.9840
        delivered_at  = now - timezone.timedelta(days=2, hours=1)

        self._create_static_parcel(
            owner=owner,
            tracking_number="DEMO-DELIVERED-US",
            carrier="FedEx",
            description="Matériel photo — livré à Manhattan",
            origin_country="DE",
            dest_country="US",
            status="delivered",
            last_live_lat=delivered_lat,
            last_live_lng=delivered_lng,
            last_live_at=delivered_at,
            events_data=[
                {
                    "timestamp": now - timezone.timedelta(days=4),
                    "location": "Frankfurt — hub FedEx Europe",
                    "lat": 50.0379, "lng": 8.5622,
                    "status": "in_transit",
                    "description": "Départ depuis Frankfurt sur vol fret FedEx",
                },
                {
                    "timestamp": now - timezone.timedelta(days=3),
                    "location": "New York JFK — hub FedEx",
                    "lat": 40.6413, "lng": -73.7781,
                    "status": "in_transit",
                    "description": "Arrivée aux États-Unis, dédouanement validé",
                },
                {
                    "timestamp": now - timezone.timedelta(days=2, hours=4),
                    "location": "FedEx — Manhattan distribution center",
                    "lat": 40.7580, "lng": -73.9855,
                    "status": "out_for_delivery",
                    "description": "Colis en cours de livraison",
                },
                {
                    "timestamp": delivered_at,
                    "location": "Midtown Manhattan, New York",
                    "lat": delivered_lat, "lng": delivered_lng,
                    "status": "delivered",
                    "description": "Colis remis au destinataire. Signé: J. Morrison",
                },
            ],
            now=now,
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
            owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if not owner:
                owner = User.objects.create_superuser(
                    username="admin", email="admin@orbi7rack.local", password="admin"
                )
                self.stdout.write(self.style.WARNING("[INFO] Superuser admin/admin créé."))

        if options["reset"]:
            deleted, _ = Parcel.objects.filter(tracking_number__startswith="DEMO-").delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f"Supprimé : {deleted} colis DEMO-*"))

        tokens = options["flights"]
        now = timezone.now()

        if not tokens:
            self.stdout.write("[INFO] Aucun token fourni — création des 4 scénarios démo.")
            self._seed_hardcoded(owner, now)
        else:
            flights = [f for t in tokens if (f := self._resolve_flight(t)) is not None]
            for flight in flights:
                self._create_parcel(owner, flight, now)
            self.stdout.write(self.style.SUCCESS(
                f"\nTerminé — {len(flights)} colis créé(s). Owner: {owner.username}"
            ))
