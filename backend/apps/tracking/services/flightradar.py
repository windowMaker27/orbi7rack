import logging
from typing import Optional
from FlightRadar24 import FlightRadar24API

logger = logging.getLogger(__name__)

_api = None

def _get_api() -> FlightRadar24API:
    global _api
    if _api is None:
        _api = FlightRadar24API()
    return _api


def get_flight_live_position(flight_number: str) -> Optional[dict]:
    """
    Retourne position live depuis FlightRadar24, None si indisponible.
    flight_number : ex. 'SQ335' — on filtre par airline ICAO (3 premiers chars) 
    puis on matche le callsign.
    """
    try:
        api = _get_api()
        # Extraire le code airline IATA (2 chars) depuis le numéro de vol
        airline_iata = ''.join(filter(str.isalpha, flight_number)).upper()
        flights = api.get_flights(airline=airline_iata)
        if not flights:
            return None
        # Matcher le callsign exact (ex: SQ335 ou SQ 335)
        target = flight_number.upper().replace(' ', '')
        match = next(
            (f for f in flights if getattr(f, 'callsign', '').upper().replace(' ', '') == target),
            None
        )
        if not match:
            logger.info(f"Vol {flight_number} non trouvé parmi {len(flights)} vols {airline_iata}")
            return None
        return {
            "lat": match.latitude,
            "lng": match.longitude,
            "altitude": match.altitude,
            "speed": match.ground_speed,
            "heading": match.heading,
            "origin_iata": getattr(match, "origin_airport_iata", None),
            "destination_iata": getattr(match, "destination_airport_iata", None),
            "source": "live",
        }
    except Exception as e:
        logger.warning(f"FlightRadar24 unavailable for {flight_number}: {e}")
        return None


def get_simulated_position(origin: tuple, destination: tuple, progress: float) -> dict:
    """
    Fallback : interpolation linéaire entre deux points GPS.
    progress: float 0.0 (départ) → 1.0 (arrivée)
    """
    progress = max(0.0, min(1.0, progress))
    lat = origin[0] + (destination[0] - origin[0]) * progress
    lng = origin[1] + (destination[1] - origin[1]) * progress
    return {
        "lat": lat,
        "lng": lng,
        "altitude": None,
        "speed": None,
        "heading": None,
        "source": "simulated",
        "progress": progress,
    }
