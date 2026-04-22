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

# Centroids approximatifs par code pays ISO-2 (couvre les routes les plus fréquentes)
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


def _country_centroid(country_code: str) -> tuple[float, float] | None:
    """Retourne le centroid (lat, lng) pour un code ISO-2, ou None."""
    if not country_code:
        return None
    return COUNTRY_CENTROIDS.get(country_code.upper())


def _haversine(lat1, lng1, lat2, lng2) -> float:
    """Distance en km entre deux points GPS (formule haversine)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _compute_progress(origin: tuple, destination: tuple, current: tuple) -> float:
    """
    Estime le % de progression sur l'arc origin->destination.
    Retourne un float entre 0.0 et 0.95 (jamais 1.0 pour eviter teleportation).
    """
    total = _haversine(*origin, *destination)
    if total == 0:
        return 0.5
    done = _haversine(*origin, *current)
    return round(min(done / total, 0.95), 4)


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

        # --- Coordonnees d'arc : centroid pays (stable, pas un hub intermediaire) ---
        origin_coords = _country_centroid(parcel.origin_country)
        dest_coords   = _country_centroid(parcel.dest_country)

        # Fallback sur geo_events si les pays ne sont pas dans la table
        if not origin_coords or not dest_coords:
            geo_events = parcel.events.filter(
                latitude__isnull=False, longitude__isnull=False
            ).order_by("timestamp")
            if geo_events.count() >= 2:
                first, last = geo_events.first(), geo_events.last()
                origin_coords = origin_coords or (first.latitude, first.longitude)
                dest_coords   = dest_coords   or (last.latitude,  last.longitude)

        # --- Live (OpenSky / FR24) ---
        if parcel.flight_number:
            position = get_flight_live_position(parcel.flight_number)
            if position:
                if origin_coords and dest_coords:
                    current = (position["lat"], position["lng"])
                    position["progress"]    = _compute_progress(origin_coords, dest_coords, current)
                    position["origin"]      = {"lat": origin_coords[0], "lng": origin_coords[1]}
                    position["destination"] = {"lat": dest_coords[0],   "lng": dest_coords[1]}
                return Response(position)

        # --- Fallback : simulation temporelle ---
        if not origin_coords or not dest_coords:
            return Response(
                {"error": "Pays origine/destination inconnus et pas assez d'evenements geocodes"},
                status=404,
            )

        # Utilise geo_events pour la fenetre temporelle uniquement
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
