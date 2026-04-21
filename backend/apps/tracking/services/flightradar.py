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


def get_flight_live_position(flight_iata: str) -> Optional[dict]:
    """Retourne position live depuis FlightRadar24, None si indisponible."""
    try:
        api = _get_api()
        flights = api.get_flights(flight_iata=flight_iata)
        if not flights:
            return None
        f = flights[0]
        return {
            "lat": f.latitude,
            "lng": f.longitude,
            "altitude": f.altitude,
            "speed": f.ground_speed,
            "heading": f.heading,
            "origin_iata": getattr(f, "origin_airport_iata", None),
            "destination_iata": getattr(f, "destination_airport_iata", None),
            "source": "live",
        }
    except Exception as e:
        logger.warning(f"FlightRadar24 unavailable for {flight_iata}: {e}")
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