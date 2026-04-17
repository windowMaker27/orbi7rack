from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.api.serializers import (
    ParcelCreateSerializer,
    ParcelSerializer,
    TrackingEventSerializer,
)
from apps.tracking.models import Parcel
from apps.tracking.services.parser import sync_parcel_from_17track
from apps.tracking.services.seventeentrack import SeventeentrackClient


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