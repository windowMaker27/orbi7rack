import logging
from typing import Optional
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

OPENSKY_BASE = "https://opensky-network.org/api"
MIN_CRUISE_ALT = 5000  # m — en dessous = pas un long-courrier


def _auth() -> Optional[tuple]:
    user = getattr(settings, "OPENSKY_USER", None)
    pwd  = getattr(settings, "OPENSKY_PASS", None)
    return (user, pwd) if user and pwd else None


def get_flight_live_position(callsign: str) -> Optional[dict]:
    """
    Cherche un vol par callsign sur OpenSky Network.
    - Match STRICT : le callsign retourné doit commencer par le callsign cherché
    - Filtre altitude > 5000m (exclut hélicos, petits avions, vols locaux)
    """
    try:
        target   = callsign.upper().strip()           # ex: "SQ335"
        padded   = target.ljust(8)                    # ex: "SQ335   "
        auth     = _auth()
        resp     = httpx.get(
            f"{OPENSKY_BASE}/states/all",
            params={"callsign": padded},
            auth=auth,
            timeout=10.0,
        )
        resp.raise_for_status()
        states = (resp.json() or {}).get("states") or []

        if not states:
            logger.info(f"[OpenSky] Aucun état pour callsign={target!r}")
            return None

        for s in states:
            raw = (s[1] or "").strip().upper()

            # ── Match strict : le callsign retourné doit être exactement le nôtre ──
            if raw != target:
                logger.debug(f"[OpenSky] Ignoré (callsign mismatch): {raw!r} != {target!r}")
                continue

            on_ground = s[8]
            lat       = s[6]
            lng       = s[5]
            geo_alt   = s[13]
            baro_alt  = s[7]
            alt       = geo_alt if geo_alt is not None else baro_alt

            if on_ground or lat is None or lng is None:
                logger.info(f"[OpenSky] {raw!r} au sol ou position inconnue")
                continue

            if alt is None or alt < MIN_CRUISE_ALT:
                logger.info(f"[OpenSky] {raw!r} rejeté : alt={alt}m < {MIN_CRUISE_ALT}m")
                continue

            logger.info(f"[OpenSky] ✓ Match retenu : {raw!r} lat={lat} lng={lng} alt={alt}m")
            return {
                "lat":              lat,
                "lng":              lng,
                "altitude":         alt,
                "speed":            s[9],
                "heading":          s[10],
                "callsign":         raw,
                "origin_iata":      None,
                "destination_iata": None,
                "source":           "live",
                "provider":         "opensky",
            }

        logger.info(
            f"[OpenSky] Aucun match strict pour {target!r} "
            f"({len(states)} candidat(s) rejeté(s))"
        )
        return None

    except Exception as e:
        logger.warning(f"[OpenSky] Indisponible pour {callsign}: {e}")
        return None
