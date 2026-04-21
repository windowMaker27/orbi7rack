import logging
from typing import Optional
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

OPENSKY_BASE = "https://opensky-network.org/api"
MIN_CRUISE_ALT = 5000


def _auth() -> Optional[tuple]:
    user = getattr(settings, "OPENSKY_USER", None)
    pwd  = getattr(settings, "OPENSKY_PASS", None)
    return (user, pwd) if user and pwd else None


def get_flight_live_position(callsign: str) -> Optional[dict]:
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
        resp.raise_for_status()
        states = (resp.json() or {}).get("states") or []

        if not states:
            logger.info(f"[OpenSky] Aucun état pour callsign={target!r}")
            return None

        # LOG tous les callsigns retournés pour identifier le format exact
        logger.warning(
            f"[OpenSky] {len(states)} candidat(s) pour {target!r} : "
            + str([(s[1], s[6], s[5], s[13], s[7]) for s in states])
        )

        for s in states:
            raw     = (s[1] or "").strip().upper()
            lat     = s[6]
            lng     = s[5]
            geo_alt = s[13]
            baro_alt= s[7]
            alt     = geo_alt if geo_alt is not None else baro_alt
            on_ground = s[8]

            # Match : le callsign retourné doit contenir notre target
            if target not in raw:
                logger.debug(f"[OpenSky] Mismatch: {raw!r} ne contient pas {target!r}")
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
                "origin_iata": None, "destination_iata": None,
                "source": "live", "provider": "opensky",
            }

        logger.info(f"[OpenSky] Aucun match valide pour {target!r}")
        return None

    except Exception as e:
        logger.warning(f"[OpenSky] Erreur pour {callsign}: {e}")
        return None
