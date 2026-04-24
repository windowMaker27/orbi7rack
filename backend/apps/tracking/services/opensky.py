import logging
from typing import Optional
import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OPENSKY_BASE = "https://opensky-network.org/api"
MIN_CRUISE_ALT = 1000   # metres — couvre montee/descente
CACHE_TTL = 60          # secondes — evite de bruler le quota anonyme (400 req/jour)

# Mapping IATA prefix → ICAO callsign prefix (copie depuis flightradar.py)
IATA_TO_ICAO_PREFIX = {
    "SQ": "SIA",  "AF": "AFR",  "BA": "BAW",  "LH": "DLH",  "KL": "KLM",
    "EK": "UAE",  "QR": "QTR",  "CX": "CPA",  "JL": "JAL",  "NH": "ANA",
    "TK": "THY",  "LX": "SWR",  "OS": "AUA",  "SK": "SAS",  "AY": "FIN",
    "IB": "IBE",  "AZ": "ITY",  "UA": "UAL",  "AA": "AAL",  "DL": "DAL",
    "WN": "SWA",  "AC": "ACA",  "QF": "QFA",  "EY": "ETD",  "MS": "MSR",
    "ET": "ETH",  "RJ": "RJA",  "CI": "CAL",  "BR": "EVA",  "OZ": "AAR",
    "KE": "KAL",  "FX": "FDX",  "5X": "UPS",  "DE": "CFG",  "KZ": "KZR",
}


def _iata_to_icao_callsign(flight_number: str) -> Optional[str]:
    fn = flight_number.upper().replace(" ", "")
    prefix = fn[:2]
    number = fn[2:]
    icao = IATA_TO_ICAO_PREFIX.get(prefix)
    return f"{icao}{number}" if icao else None


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
            raw      = (s[1] or "").strip().upper()
            lat      = s[6]
            lng      = s[5]
            geo_alt  = s[13]
            baro_alt = s[7]
            alt      = geo_alt if geo_alt is not None else baro_alt
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
      1. Le callsign IATA tel quel  (ex: AF011)
      2. Le callsign ICAO converti  (ex: AFR011)
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
