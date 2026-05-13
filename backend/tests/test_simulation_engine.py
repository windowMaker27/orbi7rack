"""
Tests unitaires — simulation_engine.py
Fonctions pures (slerp, haversine) + intégration DB (compute, get_current_position).
"""
import math
import pytest
from datetime import timedelta
from django.utils import timezone
from apps.tracking.services.simulation_engine import (
    _slerp,
    _haversine_km,
    compute_parcel_simulation,
    get_current_simulated_position,
)


# ---------------------------------------------------------------------------
# _haversine_km
# ---------------------------------------------------------------------------

class TestHaversine:
    def test_same_point_is_zero(self):
        assert _haversine_km(48.85, 2.35, 48.85, 2.35) == pytest.approx(0.0, abs=1e-6)

    def test_paris_to_london(self):
        """Paris → Londres ~340 km."""
        km = _haversine_km(48.8566, 2.3522, 51.5074, -0.1278)
        assert 330 < km < 360

    def test_shanghai_to_paris(self):
        """Shanghai → Paris ~9200 km."""
        km = _haversine_km(31.23, 121.47, 48.85, 2.35)
        assert 9000 < km < 9500

    def test_antipodal_points(self):
        """Points antipodaux → demi-circonférence terrestre ~20015 km."""
        km = _haversine_km(0.0, 0.0, 0.0, 180.0)
        assert 20000 < km < 20040

    def test_north_south_pole(self):
        """Pôle Nord → Pôle Sud ~20015 km."""
        km = _haversine_km(90.0, 0.0, -90.0, 0.0)
        assert 19900 < km < 20100


# ---------------------------------------------------------------------------
# _slerp
# ---------------------------------------------------------------------------

class TestSlerp:
    def test_t_zero_returns_start(self):
        lat, lng = _slerp(48.85, 2.35, 31.23, 121.47, 0.0)
        assert lat == pytest.approx(48.85, abs=1e-4)
        assert lng == pytest.approx(2.35, abs=1e-4)

    def test_t_one_returns_end(self):
        lat, lng = _slerp(48.85, 2.35, 31.23, 121.47, 1.0)
        assert lat == pytest.approx(31.23, abs=1e-4)
        assert lng == pytest.approx(121.47, abs=1e-4)

    def test_t_half_is_between(self):
        """t=0.5 → point intermédiaire entre Paris et Shanghai."""
        lat, lng = _slerp(48.85, 2.35, 31.23, 121.47, 0.5)
        # Le point doit être entre les deux en latitude
        assert 30 < lat < 50
        # Et entre les deux en longitude (grand cercle)
        assert 2 < lng < 122

    def test_t_clamped_below_zero(self):
        """t < 0 est clampé à 0."""
        lat, lng = _slerp(48.85, 2.35, 31.23, 121.47, -1.0)
        assert lat == pytest.approx(48.85, abs=1e-4)

    def test_t_clamped_above_one(self):
        """t > 1 est clampé à 1."""
        lat, lng = _slerp(48.85, 2.35, 31.23, 121.47, 2.0)
        assert lat == pytest.approx(31.23, abs=1e-4)

    def test_identical_points_fallback_linear(self):
        """Points quasi-identiques → fallback linéaire, pas de division par zéro."""
        lat, lng = _slerp(48.85, 2.35, 48.85, 2.35, 0.5)
        assert lat == pytest.approx(48.85, abs=1e-4)
        assert lng == pytest.approx(2.35, abs=1e-4)


# ---------------------------------------------------------------------------
# compute_parcel_simulation (DB)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComputeParcelSimulation:
    def test_no_geo_events_is_noop(self, parcel):
        """Colis sans events géocodés → pas d'erreur, rien ne change."""
        compute_parcel_simulation(parcel)
        from apps.tracking.models import TrackingEvent
        assert not TrackingEvent.objects.filter(parcel=parcel, simulated=True).exists()

    def test_single_geo_event(self, parcel):
        """1 seul event géocodé → estimated_departure = estimated_arrival (segment nul)."""
        from apps.tracking.models import TrackingEvent
        now = timezone.now()
        ev = TrackingEvent.objects.create(
            parcel=parcel,
            timestamp=now,
            latitude=31.23, longitude=121.47,
            status="Departed",
            description="Seul event",
        )
        compute_parcel_simulation(parcel)
        ev.refresh_from_db()
        assert ev.simulated is True
        assert ev.estimated_departure == ev.estimated_arrival

    def test_multiple_events_chain(self, parcel_with_events):
        """3 events → estimated_arrival[i] == estimated_departure[i+1]."""
        from apps.tracking.models import TrackingEvent
        compute_parcel_simulation(parcel_with_events)

        events = list(
            TrackingEvent.objects
            .filter(parcel=parcel_with_events, simulated=True)
            .order_by("timestamp")
        )
        assert len(events) == 3

        # Chaîne de segments
        assert events[0].estimated_arrival == events[1].estimated_departure
        assert events[1].estimated_arrival == events[2].estimated_departure

        # Dernier event : arr == dep (segment nul)
        assert events[2].estimated_departure == events[2].estimated_arrival

    def test_all_events_marked_simulated(self, parcel_with_events):
        compute_parcel_simulation(parcel_with_events)
        from apps.tracking.models import TrackingEvent
        events = TrackingEvent.objects.filter(parcel=parcel_with_events)
        for ev in events:
            assert ev.simulated is True

    def test_idempotent(self, parcel_with_events):
        """Appeler compute deux fois ne doit pas créer de doublons ni d'erreur."""
        compute_parcel_simulation(parcel_with_events)
        compute_parcel_simulation(parcel_with_events)
        from apps.tracking.models import TrackingEvent
        count = TrackingEvent.objects.filter(parcel=parcel_with_events, simulated=True).count()
        assert count == 3


# ---------------------------------------------------------------------------
# get_current_simulated_position (DB)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetCurrentSimulatedPosition:
    def test_returns_none_without_events(self, parcel):
        result = get_current_simulated_position(parcel)
        assert result is None

    def test_returns_position_during_transit(self, parcel_with_events):
        """Avec events en cours (timestamps passé → futur), doit retourner une position."""
        compute_parcel_simulation(parcel_with_events)
        result = get_current_simulated_position(parcel_with_events)
        assert result is not None
        assert "lat" in result
        assert "lng" in result
        assert "progress" in result
        assert 0.0 <= result["progress"] <= 1.0
        assert result["source"] == "simulated"

    def test_returns_last_position_after_delivery(self, parcel):
        """Si now > dernier estimated_arrival → retourne la position du dernier event."""
        from apps.tracking.models import TrackingEvent
        # Event dans le passé lointain
        past = timezone.now() - timedelta(days=30)
        ev = TrackingEvent.objects.create(
            parcel=parcel,
            timestamp=past,
            latitude=48.85, longitude=2.35,
            status="Delivered",
            description="Livré",
            estimated_departure=past,
            estimated_arrival=past,  # déjà dépassé
            simulated=True,
        )
        result = get_current_simulated_position(parcel)
        assert result is not None
        assert result["progress"] == 1.0
        assert result["lat"] == pytest.approx(48.85)
        assert result["lng"] == pytest.approx(2.35)

    def test_progress_is_global(self, parcel_with_events):
        """Progress globale = (segment_actif + t_local) / total_segments."""
        compute_parcel_simulation(parcel_with_events)
        result = get_current_simulated_position(parcel_with_events)
        # 3 segments → progress max = 1.0
        assert 0.0 <= result["progress"] <= 1.0

    def test_segment_index_in_result(self, parcel_with_events):
        compute_parcel_simulation(parcel_with_events)
        result = get_current_simulated_position(parcel_with_events)
        assert "segment_index" in result
        assert "segment_total" in result
        assert result["segment_total"] == 3
