from rest_framework import serializers
from django.utils import timezone

from apps.tracking.models import Parcel, TrackingEvent

# Centroïdes ISO2 pour le fallback de position
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
    "PL": (51.91, 19.14), "PT": (39.39, -8.22), "RE": (-21.11, 55.53),
    "RO": (45.94, 24.96), "RU": (61.52, 105.31), "SA": (23.88, 45.07),
    "SE": (60.12, 18.64), "SG": (1.35, 103.81), "SK": (48.66, 19.69),
    "TH": (15.87, 100.99), "TR": (38.96, 35.24), "TW": (23.69, 120.96),
    "UA": (48.37, 31.16), "US": (37.09, -95.71), "VN": (14.05, 108.27),
    "ZA": (-28.47, 24.67),
}

# Préfixes de tracking number → pays destination
# Ex: CNFR → China→France, CNDE → China→Germany
_TRACKING_PREFIX_DEST = {
    "CNFR": "FR", "CNDE": "DE", "CNGB": "GB", "CNUS": "US",
    "CNPL": "PL", "CNNL": "NL", "CNES": "ES", "CNIT": "IT",
    "CNBE": "BE", "CNPT": "PT", "CNSE": "SE", "CNCH": "CH",
    "CNAT": "AT", "CNCA": "CA", "CNAU": "AU", "CNJP": "JP",
    "CNKR": "KR", "CNSG": "SG", "CNHK": "HK",
}


def get_centroid(country_code: str):
    if not country_code:
        return None
    return ISO2_CENTROIDS.get(country_code.upper())


def _resolve_dest_country(obj) -> str:
    """Retourne le code pays destination, en fallback sur le préfixe du tracking number."""
    if obj.dest_country:
        return obj.dest_country.upper()
    tn = (obj.tracking_number or "").upper()
    for prefix, country in _TRACKING_PREFIX_DEST.items():
        if tn.startswith(prefix):
            return country
    return ""


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
            "transport_mode",
            "flight_iata",
            "estimated_departure",
            "estimated_arrival",
            "simulated",
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
        """Events géocodés triés ASC, dédupliqués par (lat, lng) consécutifs."""
        raw = [
            e for e in sorted(obj.events.all(), key=lambda e: e.timestamp)
            if e.latitude is not None and e.longitude is not None
        ]
        # Déduplication : on ignore les events consécutifs avec exactement les mêmes coords
        deduped = []
        for e in raw:
            if not deduped or (e.latitude, e.longitude) != (deduped[-1].latitude, deduped[-1].longitude):
                deduped.append(e)
        return deduped

    def get_origin_coords(self, obj):
        geo = self._geo_events(obj)
        if geo:
            e = geo[0]
            return {"lat": e.latitude, "lng": e.longitude, "source": "event"}
        pos = get_centroid(obj.origin_country)
        if pos:
            return {"lat": pos[0], "lng": pos[1], "source": "centroid"}
        return None

    def get_dest_coords(self, obj):
        """Coordonnées destination — chaîne de fallbacks robuste :
        1. Dernier event géocodé distinct (dédupliqué) si ≥2 events distincts
        2. Centroïde dest_country (ou pays résolu via préfixe tracking number)
        3. Seul event géocodé disponible
        """
        geo = self._geo_events(obj)

        if len(geo) >= 2:
            e = geo[-1]
            return {"lat": e.latitude, "lng": e.longitude, "source": "event"}

        # Fallback pays : dest_country ou préfixe tracking number
        dest_country = _resolve_dest_country(obj)
        pos = get_centroid(dest_country)
        if pos:
            return {"lat": pos[0], "lng": pos[1], "source": "centroid"}

        # Dernier recours : seul event disponible
        if geo:
            e = geo[-1]
            return {"lat": e.latitude, "lng": e.longitude, "source": "event_single"}

        return None

    def get_estimated_position(self, obj):
        """
        Priorité :
        1. SimulationEngine (segments temporels avec slerp) — si des events simulated=True existent
        2. Colis delivered → centroïde dest_country
        3. Dernier event géocodé (statique)
        4. Centroïde origin_country
        """
        # 1. SimulationEngine
        simulated_events = [
            e for e in obj.events.all()
            if getattr(e, 'simulated', False) and e.latitude is not None
        ]
        if simulated_events:
            try:
                from apps.tracking.services.simulation_engine import get_current_simulated_position
                result = get_current_simulated_position(obj)
                if result:
                    return result
            except Exception:
                pass

        # 2. Delivered
        if obj.status == Parcel.Status.DELIVERED:
            dest_country = _resolve_dest_country(obj)
            pos = get_centroid(dest_country)
            if pos:
                return {"lat": pos[0], "lng": pos[1], "source": "dest_country", "progress": 1.0}

        # 3. Dernier event géocodé
        geo_event = next(
            (e for e in obj.events.all() if e.latitude is not None and e.longitude is not None),
            None
        )
        if geo_event:
            return {
                "lat": geo_event.latitude,
                "lng": geo_event.longitude,
                "source": "last_event",
                "progress": None,
            }

        # 4. Centroïde origin
        pos = get_centroid(obj.origin_country)
        if pos:
            return {"lat": pos[0], "lng": pos[1], "source": "origin_country", "progress": 0.0}

        return None


class ParcelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcel
        fields = ["tracking_number", "carrier", "description"]
