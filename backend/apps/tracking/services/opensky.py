import logging
from typing import Optional
import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OPENSKY_BASE   = "https://opensky-network.org/api"
MIN_CRUISE_ALT = 1000  # metres
CACHE_TTL      = 60    # secondes

IATA_TO_ICAO_PREFIX = {
    "SQ": "SIA",  "AF": "AFR",  "BA": "BAW",  "LH": "DLH",  "KL": "KLM",
    "EK": "UAE",  "QR": "QTR",  "CX": "CPA",  "JL": "JAL",  "NH": "ANA",
    "TK": "THY",  "LX": "SWR",  "OS": "AUA",  "SK": "SAS",  "AY": "FIN",
    "IB": "IBE",  "AZ": "ITY",  "UA": "UAL",  "AA": "AAL",  "DL": "DAL",
    "WN": "SWA",  "AC": "ACA",  "QF": "QFA",  "EY": "ETD",  "MS": "MSR",
    "ET": "ETH",  "RJ": "RJA",  "CI": "CAL",  "BR": "EVA",  "OZ": "AAR",
    "KE": "KAL",  "FX": "FDX",  "5X": "UPS",  "DE": "CFG",  "KZ": "KZR",
    "AI": "AIC",  "6E": "IGO",  "UK": "VTI",  "EI": "EIN",  "VY": "VLG",
    "U2": "EZY",  "FR": "RYR",  "W6": "WZZ",  "TP": "TAP",  "SN": "BEL",
    "LO": "LOT",  "OK": "CSA",  "MH": "MAS",  "GA": "GIA",  "PR": "PAL",
    "VN": "HVN",  "TG": "THA",  "SV": "SVA",  "GF": "GFA",  "WY": "OMA",
    "PK": "PIA",  "UL": "ALK",  "CM": "CMP",  "AV": "AVA",  "LA": "LAN",
    "G3": "GLO",  "AD": "AZU",  "AR": "ARG",  "AM": "AMX",  "SA": "SAA",
    "KQ": "KQA",  "RO": "ROT",  "SU": "AFL",  "S7": "SBI",  "HY": "UZB",
}


def _iata_to_icao_callsign(flight_number: str) -> Optional[str]:
    fn = flight_number.upper().replace(" ", "")
    for n in (2, 1):
        prefix = fn[:n]
        icao = IATA_TO_ICAO_PREFIX.get(prefix)
        if icao:
            return f"{icao}{fn[n:]}"
    return None


def _auth() -> Optional[tuple]:
    """Retourne (username, password) si dispo, sinon None (mode anonyme)."""
    username = getattr(settings, "OPENSKY_USER", "") or ""
    password = getattr(settings, "OPENSKY_PASS", "") or ""
    if username and password:
        return (username, password)
    logger.warning("[OpenSky] Credentials absents — mode anonyme (quota réduit)")
    return None


def _query_opensky(callsign: str) -> Optional[dict]:
    target = callsign.upper().strip()
    padded = target.ljust(8)
    auth   = _auth()

    try:
        resp = httpx.get(
            f"{OPENSKY_BASE}/states/all",
            params={"callsign": padded},
            auth=auth,
            timeout=10.0,
        )

        if resp.status_code == 429:
            retry = resp.headers.get("X-Rate-Limit-Retry-After-Seconds", "?")
            logger.warning(f"[OpenSky] 429 Rate limit — retry after {retry}s")
            return None

        resp.raise_for_status()
        states = (resp.json() or {}).get("states") or []

        if not states:
            logger.info(f"[OpenSky] Aucun état pour callsign={target!r}")
            return None

        logger.debug(
            f"[OpenSky] {len(states)} candidat(s) pour {target!r} : "
            + str([(s[1], s[6], s[5], s[13], s[7]) for s in states])
        )

        for s in states:
            raw       = (s[1] or "").strip().upper()
            lat       = s[6]
            lng       = s[5]
            alt       = s[13] if s[13] is not None else s[7]
            on_ground = s[8]

            if target not in raw:
                continue
            if on_ground or lat is None or lng is None:
                logger.info(f"[OpenSky] {raw!r} au sol ou position inconnue")
                continue
            if alt is None or alt < MIN_CRUISE_ALT:
                logger.info(f"[OpenSky] {raw!r} alt={alt}m trop bas, rejeté")
                continue

            logger.info(f"[OpenSky] ✓ {raw!r} lat={lat} lng={lng} alt={alt}m")
            return {
                "lat": lat, "lng": lng,
                "altitude": alt, "speed": s[9], "heading": s[10],
                "callsign": raw,
                "source": "live", "provider": "opensky",
            }

        logger.info(f"[OpenSky] Aucun match valide pour {target!r}")
        return None

    except Exception as e:
        logger.warning(f"[OpenSky] Erreur pour {callsign!r}: {e}")
        return None


def get_flight_live_position(flight_number: str) -> Optional[dict]:
    iata = flight_number.upper().strip()
    icao = _iata_to_icao_callsign(iata)

    cache_key = f"opensky_pos_{iata}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"[OpenSky] Cache hit pour {iata!r}")
        return cached if cached is not False else None

    result = _query_opensky(iata)

    if result is None and icao and icao != iata:
        logger.debug(f"[OpenSky] Retry avec callsign ICAO: {icao!r}")
        result = _query_opensky(icao)

    cache.set(cache_key, result if result is not None else False, CACHE_TTL)
    return result
