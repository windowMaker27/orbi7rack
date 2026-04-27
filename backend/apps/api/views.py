import math
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.tracking.services.flightradar import get_flight_live_position, get_simulated_position
from django.utils import timezone
from apps.api.serializers import (
    ParcelCreateSerializer,
    ParcelSerializer,
    TrackingEventSerializer,
)
from apps.tracking.models import Parcel
from apps.tracking.services.parser import sync_parcel_from_17track
from apps.tracking.services.seventeentrack import SeventeentrackClient

# Centroids approximatifs par code pays ISO-2
COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "FR": (46.2276, 2.2137),
    "DE": (51.1657, 10.4515),
    "GB": (55.3781, -3.4360),
    "US": (37.0902, -95.7129),
    "CN": (35.8617, 104.1954),
    "JP": (36.2048, 138.2529),
    "KR": (35.9078, 127.7669),
    "HK": (22.3193, 114.1694),
    "SG": (1.3521, 103.8198),
    "AU": (-25.2744, 133.7751),
    "CA": (56.1304, -106.3468),
    "BR": (-14.2350, -51.9253),
    "IN": (20.5937, 78.9629),
    "RU": (61.5240, 105.3188),
    "ZA": (-30.5595, 22.9375),
    "MX": (23.6345, -102.5528),
    "AE": (23.4241, 53.8478),
    "NL": (52.1326, 5.2913),
    "BE": (50.5039, 4.4699),
    "ES": (40.4637, -3.7492),
    "IT": (41.8719, 12.5674),
    "PL": (51.9194, 19.1451),
    "SE": (60.1282, 18.6435),
    "CH": (46.8182, 8.2275),
    "TW": (23.6978, 120.9605),
    "TH": (15.8700, 100.9925),
    "MY": (4.2105, 101.9758),
    "TR": (38.9637, 35.2433),
    "SA": (23.8859, 45.0792),
    "PT": (39.3999, -8.2245),
    "CZ": (49.8175, 15.4730),
    "AT": (47.5162, 14.5501),
    "DK": (56.2639, 9.5018),
    "FI": (61.9241, 25.7482),
    "NO": (60.4720, 8.4689),
    "GR": (39.0742, 21.8243),
    "RO": (45.9432, 24.9668),
    "HU": (47.1625, 19.5033),
    "UA": (48.3794, 31.1656),
    "ID": (-0.7893, 113.9213),
    "PH": (12.8797, 121.7740),
    "VN": (14.0583, 108.2772),
    "PK": (30.3753, 69.3451),
    "BD": (23.6850, 90.3563),
    "EG": (26.8206, 30.8025),
    "NG": (9.0820, 8.6753),
    "KE": (-0.0236, 37.9062),
    "NZ": (-40.9006, 174.8860),
    "IL": (31.0461, 34.8516),
    "CL": (-35.6751, -71.5430),
    "AR": (-38.4161, -63.6167),
    "CO": (4.5709, -74.2973),
}

# Coordonnées des principaux aéroports IATA
AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    "LHR": (51.4700, -0.4543),
    "CDG": (49.0097, 2.5479),
    "AMS": (52.3086, 4.7639),
    "FRA": (50.0379, 8.5622),
    "MAD": (40.4936, -3.5668),
    "BCN": (41.2974, 2.0833),
    "FCO": (41.8003, 12.2389),
    "MUC": (48.3538, 11.7861),
    "ZRH": (47.4647, 8.5492),
    "VIE": (48.1103, 16.5697),
    "BRU": (50.9014, 4.4844),
    "CPH": (55.6180, 12.6508),
    "OSL": (60.1939, 11.1004),
    "ARN": (59.6519, 17.9186),
    "HEL": (60.3172, 24.9633),
    "LIS": (38.7813, -9.1359),
    "ATH": (37.9364, 23.9445),
    "IST": (41.2753, 28.7519),
    "DXB": (25.2532, 55.3657),
    "AUH": (24.4330, 54.6511),
    "DOH": (25.2609, 51.6138),
    "SIN": (1.3644, 103.9915),
    "HKG": (22.3080, 113.9185),
    "NRT": (35.7720, 140.3929),
    "HND": (35.5494, 139.7798),
    "ICN": (37.4602, 126.4407),
    "PVG": (31.1443, 121.8083),
    "PEK": (40.0799, 116.6031),
    "CAN": (23.3924, 113.2988),
    "BKK": (13.6811, 100.7472),
    "KUL": (2.7456, 101.7099),
    "CGK": (-6.1256, 106.6558),
    "MNL": (14.5086, 121.0197),
    "DEL": (28.5562, 77.1000),
    "BOM": (19.0896, 72.8656),
    "SYD": (-33.9399, 151.1753),
    "MEL": (-37.6690, 144.8410),
    "AKL": (-37.0082, 174.7917),
    "JFK": (40.6413, -73.7781),
    "LAX": (33.9425, -118.4081),
    "ORD": (41.9742, -87.9073),
    "ATL": (33.6407, -84.4277),
    "DFW": (32.8998, -97.0403),
    "MIA": (25.7959, -80.2870),
    "SFO": (37.6213, -122.3790),
    "SEA": (47.4502, -122.3088),
    "BOS": (42.3656, -71.0096),
    "YYZ": (43.6777, -79.6248),
    "YVR": (49.1967, -123.1815),
    "MEX": (19.4363, -99.0721),
    "GRU": (-23.4356, -46.4731),
    "EZE": (-34.8222, -58.5358),
    "SCL": (-33.3930, -70.7858),
    "BOG": (4.7016, -74.1469),
    "JNB": (-26.1367, 28.2411),
    "CAI": (30.1219, 31.4056),
    "SVO": (55.9736, 37.4125),
    "DME": (55.4088, 37.9063),
}


def _airport_coords(iata: str) -> tuple[float, float] | None:
    if not iata:
        return None
    return AIRPORT_COORDS.get(iata.upper())


def _country_centroid(country_code: str) -> tuple[float, float] | None:
    if not country_code:
        return None
    return COUNTRY_CENTROIDS.get(country_code.upper())


def _haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _compute_progress(origin: tuple, destination: tuple, current: tuple) -> float:
    total = _haversine(*origin, *destination)
    if total == 0:
        return 0.5
    done = _haversine(*origin, *current)
    return round(min(done / total, 0.95), 4)


def _resolve_endpoints(parcel) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    """
    Résout (origin_coords, dest_coords) pour un colis.
    Priorité : coordonnées des TrackingEvents géocodés (premier=départ, dernier=arrivée)
    Fallback : centroïde pays.
    """
    geo_events = list(
        parcel.events.filter(latitude__isnull=False, longitude__isnull=False)
        .order_by("timestamp")
    )

    if len(geo_events) >= 2:
        first, last = geo_events[0], geo_events[-1]
        origin = (first.latitude, first.longitude)
        destination = (last.latitude, last.longitude)
        return origin, destination

    # Fallback partiel : un seul event géocodé
    origin_coords = _country_centroid(parcel.origin_country)
    dest_coords = _country_centroid(parcel.dest_country)

    if len(geo_events) == 1:
        e = geo_events[0]
        if not origin_coords:
            origin_coords = (e.latitude, e.longitude)
        elif not dest_coords:
            dest_coords = (e.latitude, e.longitude)

    return origin_coords, dest_coords


class ParcelViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Parcel.objects.filter(owner=self.request.user).prefetch_related("events")

    def get_serializer_class(self):
        if self.action == "create":
            return ParcelCreateSerializer
        return ParcelSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parcel = Parcel.objects.create(
            owner=request.user,
            tracking_number=serializer.validated_data["tracking_number"],
            carrier=serializer.validated_data.get("carrier", ""),
            description=serializer.validated_data.get("description", ""),
        )

        client = SeventeentrackClient()
        client.register(parcel.tracking_number)
        payload = client.get_track_info(parcel.tracking_number)
        sync_parcel_from_17track(parcel, payload)

        output = ParcelSerializer(parcel, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        parcel = self.get_object()
        serializer = TrackingEventSerializer(parcel.events.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def refresh(self, request, pk=None):
        parcel = self.get_object()
        client = SeventeentrackClient()
        payload = client.get_track_info(parcel.tracking_number)
        sync_parcel_from_17track(parcel, payload)
        return Response(ParcelSerializer(parcel).data)

    @action(detail=True, methods=["get"])
    def flight_position(self, request, pk=None):
        parcel = self.get_object()

        # Résolution précise origine/destination via TrackingEvents
        origin_coords, dest_coords = _resolve_endpoints(parcel)

        # --- Live (OpenSky / FR24) ---
        if parcel.flight_number:
            position = get_flight_live_position(parcel.flight_number)
            if position:
                # Priorité : coords aéroports IATA retournés par le provider live
                # (plus précis et dans le bon sens que les centroïdes pays)
                live_origin_iata = position.get("origin_iata")
                live_dest_iata   = position.get("destination_iata")
                live_origin = _airport_coords(live_origin_iata)
                live_dest   = _airport_coords(live_dest_iata)

                # Fallback sur _resolve_endpoints si IATA inconnus
                final_origin = live_origin or origin_coords
                final_dest   = live_dest   or dest_coords

                if final_origin and final_dest:
                    current = (position["lat"], position["lng"])
                    position["progress"]    = _compute_progress(final_origin, final_dest, current)
                    position["origin"]      = {"lat": final_origin[0], "lng": final_origin[1]}
                    position["destination"] = {"lat": final_dest[0],   "lng": final_dest[1]}

                parcel.last_live_lat = position["lat"]
                parcel.last_live_lng = position["lng"]
                parcel.last_live_at  = timezone.now()
                parcel.save(update_fields=["last_live_lat", "last_live_lng", "last_live_at"])

                return Response(position)

            # Fallback stale DB
            if parcel.last_live_lat is not None and parcel.last_live_lng is not None:
                stale: dict = {
                    "lat":      parcel.last_live_lat,
                    "lng":      parcel.last_live_lng,
                    "altitude": None,
                    "speed":    None,
                    "heading":  None,
                    "callsign": parcel.flight_number,
                    "source":   "live",
                    "stale":    True,
                    "stale_since": parcel.last_live_at.isoformat() if parcel.last_live_at else None,
                    "provider": "db_cache",
                }
                if origin_coords and dest_coords:
                    current = (parcel.last_live_lat, parcel.last_live_lng)
                    stale["progress"]    = _compute_progress(origin_coords, dest_coords, current)
                    stale["origin"]      = {"lat": origin_coords[0], "lng": origin_coords[1]}
                    stale["destination"] = {"lat": dest_coords[0],   "lng": dest_coords[1]}
                return Response(stale)

        # --- Fallback : simulation temporelle ---
        if not origin_coords or not dest_coords:
            return Response(
                {"error": "Origine/destination inconnues et pas assez d'événements géocodés"},
                status=404,
            )

        geo_events = parcel.events.filter(
            latitude__isnull=False, longitude__isnull=False
        ).order_by("timestamp")

        if geo_events.count() >= 2:
            total_sec = (geo_events.last().timestamp - geo_events.first().timestamp).total_seconds()
            elapsed   = (timezone.now() - geo_events.first().timestamp).total_seconds()
            progress  = min(elapsed / total_sec, 0.95) if total_sec > 0 else 0.5
        else:
            progress = 0.5

        position = get_simulated_position(origin_coords, dest_coords, progress)
        position["origin"]      = {"lat": origin_coords[0], "lng": origin_coords[1]}
        position["destination"] = {"lat": dest_coords[0],   "lng": dest_coords[1]}
        return Response(position)
