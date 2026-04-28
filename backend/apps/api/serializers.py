from rest_framework import serializers

from apps.tracking.models import Parcel, TrackingEvent

# Centroïdes ISO2 pour le fallback de position (dernier recours uniquement)
ISO2_CENTROIDS = {
    "AF": (33.93, 67.71), "AL": (41.15, 20.17), "DZ": (28.03, 1.65),
    "AO": (-11.20, 17.87), "AR": (-38.41, -63.61), "AT": (47.51, 14.55),
    "AU": (-25.27, 133.77), "AZ": (40.14, 47.57), "BD": (23.68, 90.35),
    "BE": (50.50, 4.46), "BG": (42.73, 25.48), "BR": (-14.23, -51.92),
    "BY": (53.70, 27.95), "CA": (56.13, -106.34), "CH": (46.81, 8.22),
    "CL": (-35.67, -71.54), "CN": (35.86, 104.19), "CO": (4.57, -74.29),
    "CZ": (49.81, 15.47), "DE": (51.16, 10.45), "DK": (56.26, 9.50),
    "EG": (26.82, 30.80), "ES": (40.46, -3.74),
    "FI": (61.92, 25.74), "FR": (46.22, 2.21), "GB": (55.37, -3.43),
    "GR": (39.07, 21.82), "HK": (22.39, 114.10), "HR": (45.10, 15.20),
    "HU": (47.16, 19.50), "ID": (-0.78, 113.92), "IN": (20.59, 78.96),
    "IT": (41.87, 12.56), "JP": (36.20, 138.25), "KR": (35.90, 127.76),
    "MA": (31.79, -7.09), "MX": (23.63, -102.55), "MY": (4.21, 101.97),
    "NG": (9.08, 8.67), "NL": (52.13, 5.29), "NO": (60.47, 8.46),
    "NZ": (-40.90, 174.88), "PH": (12.87, 121.77), "PK": (30.37, 69.34),
    "PL": (51.91, 19.14), "PT": (39.39, -8.22), "RO": (45.94, 24.96),
    "RU": (61.52, 105.31), "SA": (23.88, 45.07), "SE": (60.12, 18.64),
    "SG": (1.35, 103.81), "SK": (48.66, 19.69), "TH": (15.87, 100.99),
    "TR": (38.96, 35.24), "TW": (23.69, 120.96), "UA": (48.37, 31.16),
    "US": (37.09, -95.71), "VN": (14.05, 108.27), "ZA": (-28.47, 24.67),
}


def get_centroid(country_code: str):
    """Retourne (lat, lng) pour un code ISO2, ou None si inconnu."""
    if not country_code:
        return None
    return ISO2_CENTROIDS.get(country_code.upper())


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
    estimated_position = serializers.SerializerMethodField()
    origin_coords = serializers.SerializerMethodField()
    dest_coords = serializers.SerializerMethodField()

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
            "estimated_position",
            "origin_coords",
            "dest_coords",
        ]
        read_only_fields = [
            "status",
            "origin_country",
            "dest_country",
            "last_synced_at",
            "created_at",
            "updated_at",
        ]

    def _geo_events(self, obj):
        """Events géocodés triés par timestamp ASC (du plus ancien au plus récent)."""
        return [
            e for e in sorted(obj.events.all(), key=lambda e: e.timestamp)
            if e.latitude is not None and e.longitude is not None
        ]

    def get_origin_coords(self, obj):
        """
        Coordonnées précises de l'origine :
        1. Premier TrackingEvent géocodé
        2. Fallback → centroïde origin_country
        """
        geo = self._geo_events(obj)
        if geo:
            e = geo[0]
            return {"lat": e.latitude, "lng": e.longitude, "source": "event"}
        pos = get_centroid(obj.origin_country)
        if pos:
            return {"lat": pos[0], "lng": pos[1], "source": "centroid"}
        return None

    def get_dest_coords(self, obj):
        """
        Coordonnées précises de la destination :
        1. Dernier TrackingEvent géocodé
        2. Fallback → centroïde dest_country
        """
        geo = self._geo_events(obj)
        if geo:
            e = geo[-1]
            return {"lat": e.latitude, "lng": e.longitude, "source": "event"}
        pos = get_centroid(obj.dest_country)
        if pos:
            return {"lat": pos[0], "lng": pos[1], "source": "centroid"}
        return None

    def get_estimated_position(self, obj):
        """
        Retourne {lat, lng, source} selon la priorité :
        1. last_live_lat/lng persisté sur le modèle (position GPS live ou seed explicite)
        2. Dernier TrackingEvent géocodé (tous statuts)
        3. Centroïde dest_country  (fallback de dernier recours, delivered ou non)
        4. Centroïde origin_country (fallback ultime)
        """
        # 1. Position live persistée (GPS avion, seed explicite, etc.)
        if obj.last_live_lat is not None and obj.last_live_lng is not None:
            return {
                "lat": obj.last_live_lat,
                "lng": obj.last_live_lng,
                "source": "last_live",
            }

        # 2. Dernier event géocodé — valable pour tous les statuts y compris delivered
        geo_event = next(
            (e for e in obj.events.all() if e.latitude is not None and e.longitude is not None),
            None,
        )
        if geo_event:
            return {"lat": geo_event.latitude, "lng": geo_event.longitude, "source": "last_event"}

        # 3. Centroïde dest_country (dernier recours si aucun event géocodé)
        pos = get_centroid(obj.dest_country)
        if pos:
            return {"lat": pos[0], "lng": pos[1], "source": "dest_centroid"}

        # 4. Centroïde origin_country (ultime)
        pos = get_centroid(obj.origin_country)
        if pos:
            return {"lat": pos[0], "lng": pos[1], "source": "origin_centroid"}

        return None


class ParcelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcel
        fields = ["tracking_number", "carrier", "description"]
