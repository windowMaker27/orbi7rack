import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Mapping IATA airline prefix → ICAO callsign prefix
# Couvre les carriers les plus fréquents dans un contexte de suivi de colis
IATA_TO_ICAO_PREFIX = {
    "SQ": "SIA",  # Singapore Airlines
    "AF": "AFR",  # Air France
    "BA": "BAW",  # British Airways
    "LH": "DLH",  # Lufthansa
    "KL": "KLM",  # KLM
    "EK": "UAE",  # Emirates
    "QR": "QTR",  # Qatar Airways
    "CX": "CPA",  # Cathay Pacific
    "JL": "JAL",  # Japan Airlines
    "NH": "ANA",  # ANA
    "TK": "THY",  # Turkish Airlines
    "LX": "SWR",  # Swiss
    "OS": "AUA",  # Austrian
    "SK": "SAS",  # Scandinavian
    "AY": "FIN",  # Finnair
    "IB": "IBE",  # Iberia
    "AZ": "ITY",  # ITA Airways
    "UA": "UAL",  # United
    "AA": "AAL",  # American
    "DL": "DAL",  # Delta
    "WN": "SWA",  # Southwest
    "AC": "ACA",  # Air Canada
    "QF": "QFA",  # Qantas
    "EY": "ETD",  # Etihad
    "MS": "MSR",  # EgyptAir
    "ET": "ETH",  # Ethiopian
    "RJ": "RJA",  # Royal Jordanian
    "CI": "CAL",  # China Airlines
    "BR": "EVA",  # EVA Air
    "OZ": "AAR",  # Asiana
    "KE": "KAL",  # Korean Air
    "FX": "FDX",  # FedEx
    "5X": "UPS",  # UPS Airlines
}


def _iata_to_icao_callsign(flight_number: str) -> Optional[str]:
    """
    Convertit un numéro de vol IATA (ex: SQ335) en callsign ICAO (ex: SIA335).
    Retourne None si le préfixe n'est pas dans la table.
    """
    flight_number = flight_number.upper().replace(" ", "")
    # Extraire le préfixe IATA (2 lettres) et le numéro
    iata_prefix = flight_number[:2]
    number = flight_number[2:]
    icao_prefix = IATA_TO_ICAO_PREFIX.get(iata_prefix)
    if icao_prefix:
        return f"{icao_prefix}{number}"
    return None


def _match_flight_in_list(flights: list, *callsigns: str) -> Optional[object]:
    """
    Cherche un vol dans une liste FR24 par callsign (essaie plusieurs variantes).
    """
    targets = {c.upper().replace(" ", "") for c in callsigns if c}
    return next(
        (f for f in flights
         if getattr(f, "callsign", "").upper().replace(" ", "") in targets),
        None,
    )


def _build_position(match, provider: str) -> dict:
    return {
        "lat": match.latitude,
        "lng": match.longitude,
        "altitude": match.altitude,
        "speed": match.ground_speed,
        "heading": match.heading,
        "origin_iata": getattr(match, "origin_airport_iata", None),
        "destination_iata": getattr(match, "destination_airport_iata", None),
        "source": "live",
        "provider": provider,
    }


def get_flight_live_position(flight_number: str) -> Optional[dict]:
    """
    Chaîne de providers : OpenSky (primaire) → FlightRadar24 (fallback).

    Pour FR24, on tente deux callsigns :
      1. Le numéro IATA tel quel       (ex: SQ335)
      2. Le callsign ICAO converti     (ex: SIA335)
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
        airline_iata = "".join(filter(str.isalpha, flight_number)).upper()

        # Variante ICAO du callsign (peut être None si préfixe inconnu)
        icao_callsign = _iata_to_icao_callsign(flight_number)

        logger.debug(
            f"FR24 lookup: IATA={flight_number.upper()} | ICAO callsign={icao_callsign}"
        )

        # Tentative 1 : filtrer par compagnie IATA (plus rapide, sous-ensemble)
        flights = api.get_flights(airline=airline_iata)
        match = _match_flight_in_list(flights, flight_number, icao_callsign)

        # Tentative 2 : si pas trouvé → dump global et recherche ICAO
        if not match and icao_callsign:
            logger.debug(
                f"FR24: pas trouvé avec airline={airline_iata}, "
                f"tentative callsign ICAO global ({icao_callsign})"
            )
            all_flights = api.get_flights()
            match = _match_flight_in_list(all_flights, icao_callsign)

        if match:
            logger.info(
                f"FR24: vol trouvé — callsign={getattr(match, 'callsign', '?')} "
                f"lat={match.latitude} lng={match.longitude}"
            )
            return _build_position(match, "flightradar24")

        logger.warning(
            f"FR24: aucun vol trouvé pour {flight_number} "
            f"(IATA) / {icao_callsign} (ICAO)"
        )

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
