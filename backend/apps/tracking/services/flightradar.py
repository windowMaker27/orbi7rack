import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_flight_live_position(flight_number: str) -> Optional[dict]:
    """
    Chaîne de providers : OpenSky (primaire) → FlightRadar24 (fallback).
    Retourne la position live ou None si tous les providers sont indisponibles.
    """
    from apps.tracking.services.opensky import get_flight_live_position as opensky_get
    position = opensky_get(flight_number)
    if position:
        return position

    # Fallback FlightRadar24
    try:
        from FlightRadar24 import FlightRadar24API
        api = FlightRadar24API()
        airline_iata = ''.join(filter(str.isalpha, flight_number)).upper()
        flights = api.get_flights(airline=airline_iata)
        if flights:
            target = flight_number.upper().replace(' ', '')
            match = next(
                (f for f in flights
                 if getattr(f, 'callsign', '').upper().replace(' ', '') == target),
                None
            )
            if match:
                return {
                    "lat": match.latitude,
                    "lng": match.longitude,
                    "altitude": match.altitude,
                    "speed": match.ground_speed,
                    "heading": match.heading,
                    "origin_iata": getattr(match, "origin_airport_iata", None),
                    "destination_iata": getattr(match, "destination_airport_iata", None),
                    "source": "live",
                    "provider": "flightradar24",
                }
    except Exception as e:
        logger.warning(f"FlightRadar24 indisponible pour {flight_number}: {e}")

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
