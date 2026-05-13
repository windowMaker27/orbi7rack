"""
Tests unitaires — serializers.py
(get_dest_coords, get_origin_coords, get_estimated_position, fallbacks ISO2)
"""
import pytest
from apps.api.serializers import (
    ParcelSerializer,
    get_centroid,
    _resolve_dest_country,
    ISO2_CENTROIDS,
)
from apps.tracking.models import Parcel, TrackingEvent
from django.utils import timezone
from datetime import timedelta


# ---------------------------------------------------------------------------
# get_centroid
# ---------------------------------------------------------------------------

class TestGetCentroid:
    def test_known_country_fr(self):
        pos = get_centroid("FR")
        assert pos is not None
        assert abs(pos[0] - 46.22) < 0.5
        assert abs(pos[1] - 2.21) < 0.5

    def test_known_country_de(self):
        pos = get_centroid("DE")
        assert pos is not None
        assert abs(pos[0] - 51.16) < 0.5

    def test_known_country_cn(self):
        pos = get_centroid("CN")
        assert pos is not None

    def test_unknown_country_returns_none(self):
        assert get_centroid("XX") is None
        assert get_centroid("ZZ") is None

    def test_empty_string_returns_none(self):
        assert get_centroid("") is None

    def test_case_insensitive(self):
        assert get_centroid("fr") == get_centroid("FR")


# ---------------------------------------------------------------------------
# _resolve_dest_country
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestResolveDestCountry:
    def _parcel(self, tracking_number, dest_country=""):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username=f"u_{tracking_number[:6]}", password="pass",
            email=f"{tracking_number[:6]}@test.com"
        )
        return Parcel.objects.create(
            tracking_number=tracking_number,
            owner=user,
            dest_country=dest_country,
            status=Parcel.Status.PENDING,
        )

    def test_explicit_dest_country_used(self):
        p = self._parcel("CNFR0000000001", dest_country="DE")
        assert _resolve_dest_country(p) == "DE"  # explicit beats prefix

    def test_prefix_cnfr_resolves_fr(self):
        p = self._parcel("CNFR9999999999", dest_country="")
        assert _resolve_dest_country(p) == "FR"

    def test_prefix_cngb_resolves_gb(self):
        p = self._parcel("CNGB1234567890", dest_country="")
        assert _resolve_dest_country(p) == "GB"

    def test_prefix_cnde_resolves_de(self):
        p = self._parcel("CNDE1234567890", dest_country="")
        assert _resolve_dest_country(p) == "DE"

    def test_unknown_prefix_returns_empty(self):
        p = self._parcel("ZZZZ1234567890", dest_country="")
        assert _resolve_dest_country(p) == ""


# ---------------------------------------------------------------------------
# ParcelSerializer.get_dest_coords
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSerializerDestCoords:
    def _serialize(self, parcel):
        return ParcelSerializer(parcel).data

    def test_dest_coords_with_dest_country_de(self, db):
        """dest_country='DE' sans events → centroïde Allemagne."""
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="u_de", password="pass", email="de@test.com"
        )
        parcel = Parcel.objects.create(
            tracking_number="CNDE0000000001",
            owner=user,
            dest_country="DE",
            status=Parcel.Status.IN_TRANSIT,
        )
        data = self._serialize(parcel)
        assert data["dest_coords"] is not None
        assert abs(data["dest_coords"]["lat"] - 51.16) < 1.0
        assert data["dest_coords"]["source"] == "centroid"

    def test_dest_coords_fallback_prefix_cnfr(self, parcel):
        """Sans dest_country, préfixe CNFR → France."""
        parcel.dest_country = ""
        parcel.save()
        data = self._serialize(parcel)
        assert data["dest_coords"] is not None
        assert abs(data["dest_coords"]["lat"] - 46.22) < 1.0

    def test_dest_coords_uses_last_event_when_2_or_more(self, parcel_with_events):
        """Avec ≥2 events géocodés distincts → dernier event."""
        data = self._serialize(parcel_with_events)
        dest = data["dest_coords"]
        assert dest is not None
        assert dest["source"] == "event"
        # Paris CDG ~ 48.85
        assert abs(dest["lat"] - 48.85) < 1.0

    def test_dest_coords_none_when_no_data(self, db):
        """Colis sans events ni pays → None."""
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="u_nodata", password="pass", email="nodata@test.com"
        )
        parcel = Parcel.objects.create(
            tracking_number="ZZZZ0000000001",
            owner=user,
            dest_country="",
            origin_country="",
            status=Parcel.Status.PENDING,
        )
        data = self._serialize(parcel)
        assert data["dest_coords"] is None

    def test_origin_coords_from_first_event(self, parcel_with_events):
        """origin_coords = premier event géocodé (Shanghai)."""
        data = self._serialize(parcel_with_events)
        origin = data["origin_coords"]
        assert origin is not None
        assert origin["source"] == "event"
        # Shanghai ~ 31.23
        assert abs(origin["lat"] - 31.23) < 1.0

    def test_origin_coords_centroid_fallback(self, parcel):
        """Sans events, origin_coords = centroïde CN."""
        data = self._serialize(parcel)
        origin = data["origin_coords"]
        assert origin is not None
        assert origin["source"] == "centroid"
        assert abs(origin["lat"] - 35.86) < 1.0


# ---------------------------------------------------------------------------
# get_estimated_position edge cases
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSerializerEstimatedPosition:
    def test_delivered_returns_dest_centroid(self, parcel):
        """Status DELIVERED → centroïde dest_country, progress=1.0."""
        parcel.status = Parcel.Status.DELIVERED
        parcel.dest_country = "FR"
        parcel.save()
        data = ParcelSerializer(parcel).data
        pos = data["estimated_position"]
        assert pos is not None
        assert pos["progress"] == 1.0
        assert pos["source"] == "dest_country"

    def test_no_data_returns_origin_centroid(self, db):
        """Sans events ni simulé, fallback = centroïde origin."""
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="u_fallback", password="pass", email="fallback@test.com"
        )
        parcel = Parcel.objects.create(
            tracking_number="CNFR_FALLBACK001",
            owner=user,
            origin_country="CN",
            dest_country="FR",
            status=Parcel.Status.PENDING,
        )
        data = ParcelSerializer(parcel).data
        pos = data["estimated_position"]
        assert pos is not None
        assert pos["progress"] == 0.0
        assert pos["source"] == "origin_country"
