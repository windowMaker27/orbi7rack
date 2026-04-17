import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from celery import shared_task
from apps.tracking.models import TrackingEvent

# Mapping codes 17Track → (ISO, lat, lng, nom)
COUNTRY_CODES_17TRACK = {
    0:   ("", None, None, ""),
    100: ("CN", 35.86, 104.19, "Chine"),
    200: ("US", 37.09, -95.71, "États-Unis"),
    201: ("GB", 55.37, -3.43, "Royaume-Uni"),
    202: ("DE", 51.16, 10.45, "Allemagne"),
    203: ("FR", 46.22, 2.21, "France"),
    204: ("IT", 41.87, 12.56, "Italie"),
    205: ("ES", 40.46, -3.74, "Espagne"),
    206: ("NL", 52.13, 5.29, "Pays-Bas"),
    207: ("BE", 50.50, 4.46, "Belgique"),
    208: ("CH", 46.81, 8.22, "Suisse"),
    209: ("AT", 47.51, 14.55, "Autriche"),
    210: ("SE", 60.12, 18.64, "Suède"),
    211: ("NO", 60.47, 8.46, "Norvège"),
    212: ("DK", 56.26, 9.50, "Danemark"),
    213: ("FI", 61.92, 25.74, "Finlande"),
    214: ("PT", 39.39, -8.22, "Portugal"),
    215: ("PL", 51.91, 19.14, "Pologne"),
    216: ("CZ", 49.81, 15.47, "République tchèque"),
    217: ("SK", 48.66, 19.69, "Slovaquie"),
    218: ("HU", 47.16, 19.50, "Hongrie"),
    219: ("RO", 45.94, 24.96, "Roumanie"),
    220: ("BG", 42.73, 25.48, "Bulgarie"),
    221: ("HR", 45.10, 15.20, "Croatie"),
    222: ("GR", 39.07, 21.82, "Grèce"),
    223: ("TR", 38.96, 35.24, "Turquie"),
    224: ("RU", 61.52, 105.31, "Russie"),
    225: ("UA", 48.37, 31.16, "Ukraine"),
    300: ("JP", 36.20, 138.25, "Japon"),
    301: ("KR", 35.90, 127.76, "Corée du Sud"),
    302: ("SG", 1.35, 103.81, "Singapour"),
    303: ("AU", -25.27, 133.77, "Australie"),
    304: ("NZ", -40.90, 174.88, "Nouvelle-Zélande"),
    305: ("MY", 4.21, 101.97, "Malaisie"),
    306: ("TH", 15.87, 100.99, "Thaïlande"),
    307: ("VN", 14.05, 108.27, "Vietnam"),
    308: ("ID", -0.78, 113.92, "Indonésie"),
    309: ("PH", 12.87, 121.77, "Philippines"),
    310: ("IN", 20.59, 78.96, "Inde"),
    311: ("PK", 30.37, 69.34, "Pakistan"),
    312: ("BD", 23.68, 90.35, "Bangladesh"),
    400: ("BR", -14.23, -51.92, "Brésil"),
    401: ("MX", 23.63, -102.55, "Mexique"),
    402: ("AR", -38.41, -63.61, "Argentine"),
    403: ("CL", -35.67, -71.54, "Chili"),
    404: ("CO", 4.57, -74.29, "Colombie"),
    500: ("ZA", -28.47, 24.67, "Afrique du Sud"),
    501: ("NG", 9.08, 8.67, "Nigéria"),
    502: ("EG", 26.82, 30.80, "Égypte"),
    503: ("MA", 31.79, -7.09, "Maroc"),
    600: ("CA", 56.13, -106.34, "Canada"),
    605: ("FR", 46.22, 2.21, "France"),  # code alternatif FR
}

_geolocator = Nominatim(user_agent="orbi7rack-tracker", timeout=5)

def country_code_to_iso(code_17track: int) -> tuple:
    """Retourne (iso2, lat, lng, nom) depuis un code 17Track."""
    try:
        return COUNTRY_CODES_17TRACK.get(int(code_17track), ("", None, None, ""))
    except (ValueError, TypeError):
        return ("", None, None, "")

def geocode_location(location_str: str, retries: int = 2) -> tuple:
    """
    Geocode une string de localisation (ville, pays...).
    Retourne (latitude, longitude) ou (None, None).
    """
    if not location_str or not location_str.strip():
        return (None, None)

    for attempt in range(retries):
        try:
            result = _geolocator.geocode(location_str)
            if result:
                return (result.latitude, result.longitude)
            return (None, None)
        except GeocoderTimedOut:
            if attempt < retries - 1:
                time.sleep(1)
            continue
        except GeocoderUnavailable:
            return (None, None)

    return (None, None)

@shared_task
def geocode_event(event_id: int):
    try:
        event = TrackingEvent.objects.get(id=event_id)
        if event.location and not event.latitude:
            lat, lng = geocode_location(event.location)
            if lat:
                event.latitude = lat
                event.longitude = lng
                event.save(update_fields=["latitude", "longitude"])
    except TrackingEvent.DoesNotExist:
        pass