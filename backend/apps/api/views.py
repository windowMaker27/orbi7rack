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
    Estime le % de progression sur l'arc origin→destination
    en projetant la position actuelle sur le segment géodésique.
    Retourne un float entre 0.0 et 1.0.
    """
    total = _haversine(*origin, *destination)
    if total == 0:
        return 0.5
    done = _haversine(*origin, *current)
    return round(min(done / total, 1.0), 4)


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

        # Récupère les events géocodés (départ = premier, arrivée = dernier)
        geo_events = parcel.events.filter(
            latitude__isnull=False, longitude__isnull=False
        ).order_by("timestamp")

        origin_coords = dest_coords = None
        if geo_events.count() >= 2:
            first, last = geo_events.first(), geo_events.last()
            origin_coords = (first.latitude, first.longitude)
            dest_coords   = (last.latitude, last.longitude)

        # --- Live (OpenSky / FR24) ---
        if parcel.flight_number:
            position = get_flight_live_position(parcel.flight_number)
            if position:
                # Enrichissement : progress géodésique + origin/destination
                if origin_coords and dest_coords:
                    current = (position["lat"], position["lng"])
                    position["progress"]    = _compute_progress(origin_coords, dest_coords, current)
                    position["origin"]      = {"lat": origin_coords[0], "lng": origin_coords[1]}
                    position["destination"] = {"lat": dest_coords[0],   "lng": dest_coords[1]}
                return Response(position)

        # --- Fallback : simulation temporelle ---
        if not origin_coords or not dest_coords:
            return Response(
                {"error": "Pas assez d'événements géocodés pour simuler la position"},
                status=404,
            )

        total_sec = (geo_events.last().timestamp - geo_events.first().timestamp).total_seconds()
        elapsed   = (timezone.now() - geo_events.first().timestamp).total_seconds()
        progress  = min(elapsed / total_sec, 1.0) if total_sec > 0 else 0.5

        position = get_simulated_position(origin_coords, dest_coords, progress)
        position["origin"]      = {"lat": origin_coords[0], "lng": origin_coords[1]}
        position["destination"] = {"lat": dest_coords[0],   "lng": dest_coords[1]}
        return Response(position)
