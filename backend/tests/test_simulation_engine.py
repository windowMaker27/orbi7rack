"""
Tests unitaires — simulation_engine.py
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
        km = _haversine_km(48.8566, 2.3522, 51.5074, -0.1278)
        assert 330 < km < 360

    def test_shanghai_to_paris(self):
        km = _haversine_km(31.23, 121.47, 48.85, 2.35)
        assert 9000 < km < 9500

    def test_antipodal_points(self):
        km = _haversine_km(0.0, 0.0, 0.0, 180.0)
        assert 20000 < km < 20040

    def test_north_south_pole(self):
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
        lat, lng = _slerp(31.23, 121.47, 48.85, 2.35, 0.5)
        assert 25.0 < lat < 75.0
        assert -180.0 <= lng <= 180.0

    def test_t_clamped_below_zero(self):
        lat, lng = _slerp(48.85, 2.35, 31.23, 121.47, -1.0)
        assert lat == pytest.approx(48.85, abs=1e-4)

    def test_t_clamped_above_one(self):
        lat, lng = _slerp(48.85, 2.35, 31.23, 121.47, 2.0)
        assert lat == pytest.approx(31.23, abs=1e-4)

    def test_identical_points_fallback_linear(self):
        lat, lng = _slerp(48.85, 2.35, 48.85, 2.35, 0.5)
        assert lat == pytest.approx(48.85, abs=1e-4)
        assert lng == pytest.approx(2.35, abs=1e-4)


# ---------------------------------------------------------------------------
# compute_parcel_simulation (DB)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComputeParcelSimulation:
    def test_no_geo_events_is_noop(self, parcel):
        compute_parcel_simulation(parcel)
        from apps.tracking.models import TrackingEvent
        assert not TrackingEvent.objects.filter(parcel=parcel, simulated=True).exists()

    def test_single_geo_event(self, parcel):
        from apps.tracking.models import TrackingEvent
        now = timezone.now()
        ev = TrackingEvent.objects.create(
            parcel=parcel, timestamp=now,
            latitude=31.23, longitude=121.47,
            status="Departed", description="Seul event",
        )
        compute_parcel_simulation(parcel)
        ev.refresh_from_db()
        assert ev.simulated is True
        assert ev.estimated_departure == ev.estimated_arrival

    def test_multiple_events_chain(self, parcel_with_events):
        from apps.tracking.models import TrackingEvent
        compute_parcel_simulation(parcel_with_events)
        events = list(
            TrackingEvent.objects
            .filter(parcel=parcel_with_events, simulated=True)
            .order_by("timestamp")
        )
        assert len(events) == 3
        assert events[0].estimated_arrival == events[1].estimated_departure
        assert events[1].estimated_arrival == events[2].estimated_departure
        assert events[2].estimated_departure == events[2].estimated_arrival

    def test_all_events_marked_simulated(self, parcel_with_events):
        compute_parcel_simulation(parcel_with_events)
        from apps.tracking.models import TrackingEvent
        for ev in TrackingEvent.objects.filter(parcel=parcel_with_events):
            assert ev.simulated is True

    def test_idempotent(self, parcel_with_events):
        compute_parcel_simulation(parcel_with_events)
        compute_parcel_simulation(parcel_with_events)
        from apps.tracking.models import TrackingEvent
        count = TrackingEvent.objects.filter(parcel=parcel_with_events, simulated=True).count()
        assert count == 3

    def test_unordered_events_sorted_correctly(self, parcel, db):
        """Events non triés chronologiquement → doit quand même chaîner dans le bon ordre."""
        from apps.tracking.models import TrackingEvent
        now = timezone.now()
        ev3 = TrackingEvent.objects.create(
            parcel=parcel, timestamp=now,
            latitude=48.85, longitude=2.35,
            status="Arrived", description="Paris",
        )
        ev1 = TrackingEvent.objects.create(
            parcel=parcel, timestamp=now - timedelta(days=10),
            latitude=31.23, longitude=121.47,
            status="Departed", description="Shanghai",
        )
        ev2 = TrackingEvent.objects.create(
            parcel=parcel, timestamp=now - timedelta(days=5),
            latitude=25.20, longitude=55.27,
            status="In transit", description="Dubai",
        )
        compute_parcel_simulation(parcel)
        ev1.refresh_from_db()
        ev2.refresh_from_db()
        ev3.refresh_from_db()
        assert ev1.estimated_arrival == ev2.estimated_departure
        assert ev2.estimated_arrival == ev3.estimated_departure


# ---------------------------------------------------------------------------
# get_current_simulated_position (DB)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetCurrentSimulatedPosition:
    def test_returns_none_without_events(self, parcel):
        result = get_current_simulated_position(parcel)
        assert result is None

    def test_returns_position_during_transit(self, parcel_with_events):
        compute_parcel_simulation(parcel_with_events)
        result = get_current_simulated_position(parcel_with_events)
        assert result is not None
        assert "lat" in result
        assert "lng" in result
        assert "progress" in result
        assert 0.0 <= result["progress"] <= 1.0
        assert result["source"] == "simulated"

    def test_returns_last_position_after_delivery(self, parcel):
        from apps.tracking.models import TrackingEvent
        past = timezone.now() - timedelta(days=30)
        TrackingEvent.objects.create(
            parcel=parcel, timestamp=past,
            latitude=48.85, longitude=2.35,
            status="Delivered", description="Livré",
            estimated_departure=past, estimated_arrival=past,
            simulated=True,
        )
        result = get_current_simulated_position(parcel)
        assert result is not None
        assert result["progress"] == 1.0
        assert result["lat"] == pytest.approx(48.85)
        assert result["lng"] == pytest.approx(2.35)

    def test_before_first_event_progress_is_minimum_clamp(self, parcel):
        """
        now < estimated_departure du 1er event → le moteur retourne le plancher de clamp (0.05).
        C'est intentionnel : le colis n'a pas encore décollé mais on affiche quand même
        une position non-nulle pour l'UX (il est prêt à partir).
        """
        from apps.tracking.models import TrackingEvent
        future = timezone.now() + timedelta(days=10)
        TrackingEvent.objects.create(
            parcel=parcel, timestamp=future,
            latitude=31.23, longitude=121.47,
            status="Pending", description="Pas encore parti",
            estimated_departure=future,
            estimated_arrival=future + timedelta(days=5),
            simulated=True,
        )
        result = get_current_simulated_position(parcel)
        assert result is not None
        assert result["progress"] <= 0.1
        assert result["lat"] == pytest.approx(31.23)
        assert result["lng"] == pytest.approx(121.47)  # Shanghai longitude

    def test_progress_is_global(self, parcel_with_events):
        compute_parcel_simulation(parcel_with_events)
        result = get_current_simulated_position(parcel_with_events)
        assert 0.0 <= result["progress"] <= 1.0

    def test_segment_index_in_result(self, parcel_with_events):
        compute_parcel_simulation(parcel_with_events)
        result = get_current_simulated_position(parcel_with_events)
        assert "segment_index" in result
        assert "segment_total" in result
        assert result["segment_total"] == 3
