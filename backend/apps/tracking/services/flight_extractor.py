"""
Étape 1 — Extraction du numéro de vol depuis les événements 17TRACK.

Priorité :
  1. Regex sur description/location de l'event  →  ex: "UA123", "AF 447", "5X 9999"
  2. Fallback AviationStack : recherche par dep_iata + arr_iata + fenêtre ±3h

Stocke flight_iata + transport_mode sur le TrackingEvent concerné.
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping carrier 17track/nom → préfixe IATA cargo
# ---------------------------------------------------------------------------
CARRIER_IATA: dict[str, str] = {
    "ups": "5X", "fedex": "FX", "dhl": "D0", "tnt": "3V", "dpd": "D0",
    "gls": "", "chronopost": "XP", "colissimo": "", "laposte": "", "amazon": "",
    "air france": "AF", "lufthansa": "LH", "british airways": "BA",
    "emirates": "EK", "qatar airways": "QR", "singapore airlines": "SQ",
    "cathay pacific": "CX", "united airlines": "UA", "american airlines": "AA",
    "delta": "DL", "klm": "KL", "turkish airlines": "TK", "air canada": "AC",
    "etihad": "EY", "swiss": "LX", "finnair": "AY", "iberia": "IB",
    "tap": "TP", "korean air": "KE", "japan airlines": "JL", "ana": "NH",
    "china airlines": "CI", "eva air": "BR", "china southern": "CZ",
    "china eastern": "MU", "air china": "CA", "austrian": "OS",
    "brussels airlines": "SN", "alitalia": "AZ", "ita airways": "AZ",
    "virgin atlantic": "VS", "alaska airlines": "AS", "southwest": "WN",
    "saudia": "SV", "egyptair": "MS", "kenya airways": "KQ",
    "ethiopian airlines": "ET", "south african airways": "SA",
    "qantas": "QF", "air new zealand": "NZ", "thai airways": "TG",
    "malaysia airlines": "MH", "garuda": "GA", "philippine airlines": "PR",
    "vietnam airlines": "VN", "indigo": "6E", "air india": "AI",
    "aeromexico": "AM", "latam": "LA", "avianca": "AV", "copa airlines": "CM",
    "cargolux": "CV", "atlas air": "5Y", "kalitta air": "K4",
    "polar air cargo": "PO", "air bridge cargo": "RU", "silk way": "ZP",
    "cathay cargo": "CX", "menzies": "",
}

# Regex principale : 2-3 caractères + 3-4 chiffres
FLIGHT_RE = re.compile(r"\b([A-Z0-9]{2,3})\s?(\d{3,4})\b")

# ---------------------------------------------------------------------------
# Keywords transport — ROAD a priorité sur AIR
# ---------------------------------------------------------------------------

# Étape terrestre/douane/tri : ces keywords écrasent les keywords air
ROAD_KEYWORDS = re.compile(
    r"\b("
    r"truck|camion|road|route"
    r"|hub|dépôt|depot|warehouse|entrepôt"
    r"|sorting.?center|centre.?de.?tri"
    r"|out.?for.?delivery|en.?livraison|en.?cours.?de.?livraison"
    r"|distribution.?center"
    r"|linehaul|line.?haul"
    r"|local.?delivery|last.?mile"
    r"|handed.?over|remis|remise"
    r"|received.?by"
    r"|post.?office|bureau.?de.?poste"
    r"|customs.?clearance|dédouanement|import.?customs|export.?customs"
    r"|transit.?country|transit.?region"
    r")",
    re.IGNORECASE,
)

# Étape aérienne : seulement si ROAD ne matche pas d'abord
FLIGHT_KEYWORDS = re.compile(
    r"\b("
    r"flight|vol|airline"
    r"|air.?freight|air.?cargo"
    r"|loaded.?on.?flight|departed.?on.?flight|arrived.?by.?air"
    r"|aéroport|envol"
    r"|airway|airways"
    r"|iata"
    r")",
    re.IGNORECASE,
)

# Étape maritime
SEA_KEYWORDS = re.compile(
    r"\b(ship|vessel|port|sea|maritime|ocean|container|navire|mer)\b",
    re.IGNORECASE,
)


def detect_transport_mode(description: str, location: str) -> str:
    """
    Retourne 'air' | 'road' | 'sea' | 'unknown'.
    Priorité : ROAD > SEA > AIR > régex vol > unknown.
    Les étapes de douane, livraison locale, tri sont toujours 'road'.
    """
    text = f"{description} {location}"

    # ROAD en premier — écrase tout le reste
    if ROAD_KEYWORDS.search(text):
        return "road"
    if SEA_KEYWORDS.search(text):
        return "sea"
    if FLIGHT_KEYWORDS.search(text):
        return "air"
    # Pattern numéro de vol = air par défaut
    if FLIGHT_RE.search(description.upper()):
        return "air"
    return "unknown"


def extract_flight_number(description: str, location: str = "") -> Optional[str]:
    """
    Extrait le numéro de vol IATA depuis le texte.
    Ne retourne rien si le mode transport est road/sea.
    """
    # Pas de numéro de vol sur une étape terrestre ou maritime
    mode = detect_transport_mode(description, location)
    if mode in ("road", "sea"):
        return None

    text = f"{description} {location}".upper()
    matches = FLIGHT_RE.findall(text)

    for prefix, number in matches:
        if len(prefix) == 2 and prefix.isdigit():
            continue
        flight = f"{prefix}{number}"
        if re.match(r"^[A-Z]{2}\d?$", prefix) or re.match(r"^[A-Z0-9]{2,3}$", prefix):
            return flight
    return None


def fallback_aviationstack(
    dep_iata: Optional[str],
    arr_iata: Optional[str],
    carrier_name: Optional[str],
    event_time=None,
) -> Optional[str]:
    api_key = getattr(settings, "AVIATIONSTACK_API_KEY", None)
    if not api_key:
        return None

    params: dict = {"access_key": api_key, "limit": 5}
    if dep_iata:
        params["dep_iata"] = dep_iata
    if arr_iata:
        params["arr_iata"] = arr_iata
    if carrier_name:
        iata_prefix = _resolve_carrier_iata(carrier_name)
        if iata_prefix:
            params["airline_iata"] = iata_prefix
    if event_time:
        params["flight_date"] = event_time.strftime("%Y-%m-%d")

    try:
        resp = requests.get(
            "http://api.aviationstack.com/v1/flights",
            params=params, timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        flights = data.get("data", [])
        if not flights:
            return None

        ref_time = event_time or timezone.now()
        window = timedelta(hours=3)

        for f in flights:
            dep_sched  = f.get("departure", {}).get("scheduled")
            arr_sched  = f.get("arrival", {}).get("scheduled")
            flight_iata = f.get("flight", {}).get("iata")
            if not flight_iata:
                continue
            for sched_str in [dep_sched, arr_sched]:
                if not sched_str:
                    continue
                try:
                    from dateutil.parser import parse as parse_dt
                    sched = parse_dt(sched_str)
                    if sched.tzinfo is None:
                        from datetime import timezone as dtz
                        sched = sched.replace(tzinfo=dtz.utc)
                    if abs((sched - ref_time).total_seconds()) <= window.total_seconds():
                        return flight_iata
                except Exception:
                    continue

        return flights[0].get("flight", {}).get("iata")

    except requests.RequestException as e:
        logger.warning(f"[flight_extractor] AviationStack erreur : {e}")
        return None


def _resolve_carrier_iata(carrier_name: str) -> Optional[str]:
    key = carrier_name.lower().strip()
    if key in CARRIER_IATA:
        return CARRIER_IATA[key] or None
    for name, code in CARRIER_IATA.items():
        if name in key or key in name:
            return code or None
    return None


def enrich_event_flight(
    event,
    carrier_name: str = "",
    dep_iata: Optional[str] = None,
    arr_iata: Optional[str] = None,
) -> bool:
    desc = event.description or ""
    loc  = event.location or ""

    # 1. Mode de transport (ROAD > SEA > AIR)
    mode = detect_transport_mode(desc, loc)
    event.transport_mode = mode

    # 2. Pas de numéro de vol si étape terrestre/maritime
    if mode in ("road", "sea", "unknown"):
        event.flight_iata = None
        return False

    # 3. Extraction regex
    flight = extract_flight_number(desc, loc)

    # 4. Fallback AviationStack
    if not flight and (dep_iata or arr_iata or carrier_name):
        flight = fallback_aviationstack(
            dep_iata=dep_iata,
            arr_iata=arr_iata,
            carrier_name=carrier_name,
            event_time=getattr(event, "timestamp", None),
        )

    if flight:
        event.flight_iata = flight
        logger.info(
            f"[flight_extractor] {event.parcel.tracking_number} event#{event.id} → {flight} ({mode})"
        )
        return True

    return False
