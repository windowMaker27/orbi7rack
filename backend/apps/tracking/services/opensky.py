import logging
from typing import Optional
import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OPENSKY_BASE = "https://opensky-network.org/api"
MIN_CRUISE_ALT = 1000   # metres — couvre montee/descente (etait 5000)
CACHE_TTL = 60          # secondes — evite de bruler le quota anonyme (400 req/jour)


def _auth() -> Optional[httpx.BasicAuth]:
    user = getattr(settings, "OPENSKY_USER", "") or ""
    pwd  = getattr(settings, "OPENSKY_PASS", "") or ""
    if user and pwd:
        logger.debug(f"[OpenSky] Auth activee pour l'utilisateur: {user!r}")
        return httpx.BasicAuth(user, pwd)
    logger.warning("[OpenSky] Aucune auth configuree — quota anonyme (400 req/jour partages)")
    return None


def get_flight_live_position(callsign: str) -> Optional[dict]:
    target = callsign.upper().strip()
    padded = target.ljust(8)

    cache_key = f"opensky_pos_{target}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"[OpenSky] Cache hit pour {target!r}")
        return cached  # peut etre False si le dernier appel n'a rien trouve

    auth = _auth()

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
            cache.set(cache_key, False, CACHE_TTL)
            return None

        logger.warning(
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
                logger.debug(f"[OpenSky] Mismatch: {raw!r} ne contient pas {target!r}")
                continue

            if on_ground or lat is None or lng is None:
                logger.info(f"[OpenSky] {raw!r} au sol ou position inconnue")
                continue

            if alt is None or alt < MIN_CRUISE_ALT:
                logger.info(f"[OpenSky] {raw!r} alt={alt}m trop bas, rejete")
                continue

            logger.info(f"[OpenSky] ✓ {raw!r} lat={lat} lng={lng} alt={alt}m")
            result = {
                "lat": lat, "lng": lng,
                "altitude": alt, "speed": s[9], "heading": s[10],
                "callsign": raw,
                "origin_iata": None, "destination_iata": None,
                "source": "live", "provider": "opensky",
            }
            cache.set(cache_key, result, CACHE_TTL)
            return result

        logger.info(f"[OpenSky] Aucun match valide pour {target!r}")
        cache.set(cache_key, False, CACHE_TTL)
        return None

    except Exception as e:
        logger.warning(f"[OpenSky] Erreur pour {callsign}: {e}")
        # Pas de cache sur erreur reseau — on reessaie au prochain appel
        return None
