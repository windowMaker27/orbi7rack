import logging
from typing import Optional
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

OPENSKY_BASE = "https://opensky-network.org/api"


def _auth() -> Optional[tuple]:
    user = getattr(settings, "OPENSKY_USER", None)
    pwd = getattr(settings, "OPENSKY_PASS", None)
    if user and pwd:
        return (user, pwd)
    return None


def get_flight_live_position(callsign: str) -> Optional[dict]:
    """
    Cherche un vol par callsign sur OpenSky Network.
    Retourne la position live ou None si introuvable.
    callsign : ex. 'SQ335', 'AF006'
    """
    try:
        padded = callsign.upper().ljust(8)  # OpenSky attend 8 chars
        auth = _auth()
        params = {"callsign": padded}
        resp = httpx.get(
            f"{OPENSKY_BASE}/states/all",
            params=params,
            auth=auth,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        states = data.get("states")
        if not states:
            logger.info(f"OpenSky: aucun vol trouvé pour callsign={callsign}")
            return None

        # Colonnes OpenSky : [icao24, callsign, origin_country, time_position,
        #   last_contact, longitude, latitude, baro_altitude, on_ground,
        #   velocity, true_track, vertical_rate, sensors, geo_altitude,
        #   squawk, spi, position_source]
        s = states[0]
        on_ground = s[8]
        latitude = s[6]
        longitude = s[5]
        if on_ground or latitude is None or longitude is None:
            logger.info(f"OpenSky: vol {callsign} au sol ou position inconnue")
            return None

        return {
            "lat": latitude,
            "lng": longitude,
            "altitude": s[13],       # geo_altitude en mètres
            "speed": s[9],           # velocity en m/s
            "heading": s[10],        # true_track en degrés
            "origin_iata": None,     # OpenSky ne fournit pas les IATA
            "destination_iata": None,
            "source": "live",
            "provider": "opensky",
        }
    except Exception as e:
        logger.warning(f"OpenSky indisponible pour {callsign}: {e}")
        return None
