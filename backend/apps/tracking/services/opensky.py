import logging
from typing import Optional
import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OPENSKY_BASE = "https://opensky-network.org/api"
MIN_CRUISE_ALT = 1000   # metres — couvre montee/descente
CACHE_TTL = 60          # secondes — evite de bruler le quota anonyme (400 req/jour)

# Mapping IATA prefix → ICAO callsign prefix (complet)
IATA_TO_ICAO_PREFIX = {
    "SQ": "SIA",  # Singapore Airlines
    "AF": "AFR",  # Air France
    "BA": "BAW",  # British Airways
    "LH": "DLH",  # Lufthansa
    "KL": "KLM",  # KLM
    "EK": "UAE",  # Emirates
    "QR": "QTR",  # Qatar Airways
    "CX": "CPA",  # Cathay Pacific
    "JL": "JAL",  # Japan Airlines
    "NH": "ANA",  # ANA
    "TK": "THY",  # Turkish Airlines
    "LX": "SWR",  # Swiss
    "OS": "AUA",  # Austrian
    "SK": "SAS",  # Scandinavian
    "AY": "FIN",  # Finnair
    "IB": "IBE",  # Iberia
    "AZ": "ITY",  # ITA Airways
    "UA": "UAL",  # United
    "AA": "AAL",  # American
    "DL": "DAL",  # Delta
    "WN": "SWA",  # Southwest
    "AC": "ACA",  # Air Canada
    "QF": "QFA",  # Qantas
    "EY": "ETD",  # Etihad
    "MS": "MSR",  # EgyptAir
    "ET": "ETH",  # Ethiopian
    "RJ": "RJA",  # Royal Jordanian
    "CI": "CAL",  # China Airlines
    "BR": "EVA",  # EVA Air
    "OZ": "AAR",  # Asiana
    "KE": "KAL",  # Korean Air
    "FX": "FDX",  # FedEx
    "5X": "UPS",  # UPS Airlines
    "DE": "CFG",  # Condor
    "KZ": "KZR",  # Air Astana
    "AI": "AIC",  # Air India
    "6E": "IGO",  # IndiGo
    "G8": "GOW",  # Go First
    "UK": "VTI",  # Vistara
    "EI": "EIN",  # Aer Lingus
    "VY": "VLG",  # Vueling
    "U2": "EZY",  # easyJet
    "FR": "RYR",  # Ryanair
    "W6": "WZZ",  # Wizz Air
    "TP": "TAP",  # TAP Air Portugal
    "SN": "BEL",  # Brussels Airlines
    "LO": "LOT",  # LOT Polish
    "OK": "CSA",  # Czech Airlines
    "MH": "MAS",  # Malaysia Airlines
    "GA": "GIA",  # Garuda Indonesia
    "PR": "PAL",  # Philippine Airlines
    "VN": "HVN",  # Vietnam Airlines
    "TG": "THA",  # Thai Airways
    "SV": "SVA",  # Saudia
    "GF": "GFA",  # Gulf Air
    "WY": "OMA",  # Oman Air
    "PK": "PIA",  # Pakistan International
    "UL": "ALK",  # SriLankan Airlines
    "CM": "CMP",  # Copa Airlines
    "AV": "AVA",  # Avianca
    "LA": "LAN",  # LATAM
    "JJ": "TAM",  # LATAM Brasil
    "G3": "GLO",  # Gol
    "AD": "AZU",  # Azul
    "AR": "ARG",  # Aerolineas Argentinas
    "AM": "AMX",  # Aeromexico
    "SA": "SAA",  # South African Airways
    "ET": "ETH",  # Ethiopian Airlines
    "KQ": "KQA",  # Kenya Airways
    "RO": "ROT",  # TAROM
    "PS": "AUI",  # Ukraine International
    "SU": "AFL",  # Aeroflot
    "S7": "SBI",  # S7 Airlines
    "UT": "UTA",  # UTair
    "HY": "UZB",  # Uzbekistan Airways
    "KC": "KZR",  # Air Astana (IATA alt)
    "B2": "BRU",  # Belavia
}


def _iata_to_icao_callsign(flight_number: str) -> Optional[str]:
    fn = flight_number.upper().replace(" ", "")
    # Essaie préfixe 2 chars puis 1 char
    for n in (2, 1):
        prefix = fn[:n]
        icao = IATA_TO_ICAO_PREFIX.get(prefix)
        if icao:
            return f"{icao}{fn[n:]}"
    return None


def _auth() -> Optional[httpx.BasicAuth]:
    user = getattr(settings, "OPENSKY_USER", "") or ""
    pwd  = getattr(settings, "OPENSKY_PASS", "") or ""
    if user and pwd:
        logger.debug(f"[OpenSky] Auth activee pour l'utilisateur: {user!r}")
        return httpx.BasicAuth(user, pwd)
    logger.warning("[OpenSky] Aucune auth configuree — quota anonyme (400 req/jour partages)")
    return None


def _query_opensky(callsign: str, auth: Optional[httpx.BasicAuth]) -> Optional[dict]:
    """Tente un appel OpenSky pour un callsign donné. Retourne le dict position ou None."""
    target = callsign.upper().strip()
    padded = target.ljust(8)

    try:
        resp = httpx.get(
            f"{OPENSKY_BASE}/states/all",
            params={"callsign": padded},
            auth=auth,
            timeout=10.0,
        )
        resp.raise_for_status()
        states = (resp.json() or {}).get("states") or []

        if not states:
            logger.info(f"[OpenSky] Aucun etat pour callsign={target!r}")
            return None

        logger.debug(
            f"[OpenSky] {len(states)} candidat(s) pour {target!r} : "
            + str([(s[1], s[6], s[5], s[13], s[7]) for s in states])
        )

        for s in states:
            raw       = (s[1] or "").strip().upper()
            lat       = s[6]
            lng       = s[5]
            geo_alt   = s[13]
            baro_alt  = s[7]
            alt       = geo_alt if geo_alt is not None else baro_alt
            on_ground = s[8]

            if target not in raw:
                continue
            if on_ground or lat is None or lng is None:
                logger.info(f"[OpenSky] {raw!r} au sol ou position inconnue")
                continue
            if alt is None or alt < MIN_CRUISE_ALT:
                logger.info(f"[OpenSky] {raw!r} alt={alt}m trop bas, rejete")
                continue

            logger.info(f"[OpenSky] ✓ {raw!r} lat={lat} lng={lng} alt={alt}m")
            return {
                "lat": lat, "lng": lng,
                "altitude": alt, "speed": s[9], "heading": s[10],
                "callsign": raw,
                "origin_iata": None, "destination_iata": None,
                "source": "live", "provider": "opensky",
            }

        logger.info(f"[OpenSky] Aucun match valide pour {target!r}")
        return None

    except Exception as e:
        logger.warning(f"[OpenSky] Erreur pour {callsign}: {e}")
        return None


def get_flight_live_position(flight_number: str) -> Optional[dict]:
    """
    Cherche la position live sur OpenSky en tentant :
      1. Le callsign IATA tel quel  (ex: DL267)
      2. Le callsign ICAO converti  (ex: DAL267)
    Met en cache 60s pour préserver le quota anonyme.
    """
    iata = flight_number.upper().strip()
    icao = _iata_to_icao_callsign(iata)

    cache_key = f"opensky_pos_{iata}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"[OpenSky] Cache hit pour {iata!r}")
        return cached if cached is not False else None

    auth = _auth()

    # Tentative 1 : callsign IATA
    result = _query_opensky(iata, auth)

    # Tentative 2 : callsign ICAO si différent
    if result is None and icao and icao != iata:
        logger.debug(f"[OpenSky] Retry avec callsign ICAO: {icao!r}")
        result = _query_opensky(icao, auth)

    cache.set(cache_key, result if result is not None else False, CACHE_TTL)
    return result
