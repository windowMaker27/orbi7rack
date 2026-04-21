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
    - Envoie le callsign padded 8 chars (requis par l'API)
    - Filtre les résultats : retient seulement les avions en croisiere (alt > 5000m)
    - Log le callsign exact retourné pour faciliter le debug
    """
    try:
        # OpenSky attend exactement 8 chars, mais peut retourner plusieurs résultats
        padded = callsign.upper().ljust(8)
        auth   = _auth()
        resp   = httpx.get(
            f"{OPENSKY_BASE}/states/all",
            params={"callsign": padded},
            auth=auth,
            timeout=10.0,
        )
        resp.raise_for_status()
        data   = resp.json()
        states = data.get("states") or []

        if not states:
            logger.info(f"[OpenSky] Aucun état pour callsign={callsign!r}")
            return None

        # Colonnes : [icao24, callsign, origin_country, time_position,
        #   last_contact, longitude, latitude, baro_altitude, on_ground,
        #   velocity, true_track, vertical_rate, sensors, geo_altitude,
        #   squawk, spi, position_source]
        for s in states:
            raw_callsign = (s[1] or "").strip()
            on_ground    = s[8]
            lat          = s[6]
            lng          = s[5]
            geo_alt      = s[13]  # m
            baro_alt     = s[7]   # m
            alt          = geo_alt if geo_alt is not None else baro_alt

            logger.debug(
                f"[OpenSky] candidate: callsign={raw_callsign!r} "
                f"lat={lat} lng={lng} alt={alt} on_ground={on_ground}"
            )

            if on_ground or lat is None or lng is None:
                continue

            # Rejeter les avions trop bas (hélicos, petits avions locaux)
            if alt is None or alt < MIN_CRUISE_ALT:
                logger.info(
                    f"[OpenSky] Rejeté {raw_callsign!r} : alt={alt}m < {MIN_CRUISE_ALT}m"
                )
                continue

            logger.info(
                f"[OpenSky] Match retenu : callsign={raw_callsign!r} "
                f"lat={lat} lng={lng} alt={alt}m"
            )
            return {
                "lat":              lat,
                "lng":              lng,
                "altitude":         alt,
                "speed":            s[9],
                "heading":          s[10],
                "callsign":         raw_callsign,
                "origin_iata":      None,
                "destination_iata": None,
                "source":           "live",
                "provider":         "opensky",
            }

        logger.info(
            f"[OpenSky] Aucun avion en croisiere pour callsign={callsign!r} "
            f"({len(states)} candidat(s) rejete(s))"
        )
        return None

    except Exception as e:
        logger.warning(f"[OpenSky] Indisponible pour {callsign}: {e}")
        return None
