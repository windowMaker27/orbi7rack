from rest_framework import serializers

from apps.tracking.models import Parcel, TrackingEvent


class TrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingEvent
        fields = [
            "id",
            "timestamp",
            "location",
            "latitude",
            "longitude",
            "status",
            "description",
        ]


class ParcelSerializer(serializers.ModelSerializer):
    events = TrackingEventSerializer(many=True, read_only=True)

    class Meta:
        model = Parcel
        fields = [
            "id",
            "tracking_number",
            "carrier",
            "description",
            "origin_country",
            "dest_country",
            "status",
            "last_synced_at",
            "created_at",
            "updated_at",
            "events",
        ]
        read_only_fields = [
            "status",
            "origin_country",
            "dest_country",
            "last_synced_at",
            "created_at",
            "updated_at",
        ]


class ParcelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcel
        fields = ["tracking_number", "carrier", "description"]