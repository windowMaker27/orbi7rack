"""
Tests unitaires — parser.py (sync_parcel_from_17track + parse_17track_datetime)
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from apps.tracking.services.parser import (
    sync_parcel_from_17track,
    parse_17track_datetime,
    extract_event_location,
)
from apps.tracking.models import Parcel, TrackingEvent


# ---------------------------------------------------------------------------
# parse_17track_datetime
# ---------------------------------------------------------------------------

class TestParse17trackDatetime:
    def test_full_datetime(self):
        dt = parse_17track_datetime("2026-05-01 14:30:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 1
        assert dt.hour == 14

    def test_datetime_without_seconds(self):
        dt = parse_17track_datetime("2026-05-01 14:30")
        assert dt is not None
        assert dt.hour == 14
        assert dt.minute == 30

    def test_date_only(self):
        dt = parse_17track_datetime("2026-05-01")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 1

    def test_none_returns_none(self):
        assert parse_17track_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert parse_17track_datetime("") is None

    def test_whitespace_returns_none(self):
        assert parse_17track_datetime("   ") is None

    def test_unknown_format_returns_none(self):
        assert parse_17track_datetime("01/05/2026") is None
        assert parse_17track_datetime("May 1st 2026") is None
        assert parse_17track_datetime("not-a-date") is None

    def test_result_is_timezone_aware(self):
        dt = parse_17track_datetime("2026-05-01 10:00:00")
        assert dt.tzinfo is not None


# ---------------------------------------------------------------------------
# extract_event_location
# ---------------------------------------------------------------------------

class TestExtractEventLocation:
    def test_city_and_country(self):
        event = {"c": "Shanghai", "d": "CN"}
        assert extract_event_location(event) == "Shanghai, CN"

    def test_city_only(self):
        event = {"c": "Paris", "d": ""}
        assert extract_event_location(event) == "Paris"

    def test_fallback_from_description_bracket(self):
        event = {"c": "", "d": "", "z": "[Paris CDG] Vol au départ"}
        assert extract_event_location(event) == "Paris CDG"

    def test_no_location_returns_empty(self):
        event = {"c": "", "d": "", "z": "Colis en transit"}
        assert extract_event_location(event) == ""

    def test_whitespace_stripped(self):
        event = {"c": "  Berlin  ", "d": "  DE  "}
        assert extract_event_location(event) == "Berlin, DE"


# ---------------------------------------------------------------------------
# sync_parcel_from_17track
# ---------------------------------------------------------------------------

def _make_payload(tracking_number, origin=100, dest=203, status=10, events=None):
    """Helper pour construire un payload 17track minimal valide."""
    if events is None:
        events = [{
            "a": "2026-05-01 10:00:00",
            "z": "Departed from Shanghai",
            "c": "Shanghai",
            "d": "CN",
        }]
    return {
        "data": {
            "accepted": [{
                "number": tracking_number,
                "track": {
                    "e": status,
                    "b": origin,
                    "d": dest,
                    "w1": "La Poste",
                    "z1": events,
                },
            }]
        }
    }


@pytest.mark.django_db
class TestSyncParcelFrom17track:
    def test_basic_sync_updates_status(self, parcel):
        """Un sync basique met à jour le status et origin/dest country."""
        with patch("apps.tracking.tasks.geocode_event_then_simulate") as mock_task:
            mock_task.delay = MagicMock()
            with patch("apps.tracking.services.geocoding.geocode_location", return_value=(None, None)):
                result = sync_parcel_from_17track(parcel, _make_payload(parcel.tracking_number))

        assert result.status == Parcel.Status.IN_TRANSIT
        assert result.origin_country == "CN"
        assert result.dest_country == "FR"

    def test_empty_accepted_raises_value_error(self, parcel):
        """payload sans 'accepted' → ValueError."""
        payload = {"data": {"accepted": []}}
        with pytest.raises(ValueError, match="17TRACK"):
            sync_parcel_from_17track(parcel, payload)

    def test_missing_accepted_key_raises_value_error(self, parcel):
        """payload sans clé 'accepted' du tout."""
        payload = {"data": {}}
        with pytest.raises(ValueError):
            sync_parcel_from_17track(parcel, payload)

    def test_dest_country_not_overwritten_when_dest_code_zero(self, parcel):
        """
        Quand dest_code = 0 (absent / inconnu),
        dest_country existant sur le colis ne doit PAS être écrasé.
        """
        parcel.dest_country = "FR"
        parcel.save()
        payload = _make_payload(parcel.tracking_number, dest=0)

        with patch("apps.tracking.tasks.geocode_event_then_simulate") as mock_task:
            mock_task.delay = MagicMock()
            with patch("apps.tracking.services.geocoding.geocode_location", return_value=(None, None)):
                result = sync_parcel_from_17track(parcel, payload)

        result.refresh_from_db()
        assert result.dest_country == "FR"  # pas écrasé

    def test_events_created(self, parcel):
        """Un sync crée les events 17track."""
        with patch("apps.tracking.tasks.geocode_event_then_simulate") as mock_task:
            mock_task.delay = MagicMock()
            with patch("apps.tracking.services.geocoding.geocode_location", return_value=(None, None)):
                sync_parcel_from_17track(parcel, _make_payload(parcel.tracking_number))

        assert TrackingEvent.objects.filter(parcel=parcel).count() == 1

    def test_idempotent_no_duplicate_events(self, parcel):
        """Appeler sync deux fois ne crée pas de doublons (get_or_create)."""
        payload = _make_payload(parcel.tracking_number)
        with patch("apps.tracking.tasks.geocode_event_then_simulate") as mock_task:
            mock_task.delay = MagicMock()
            with patch("apps.tracking.services.geocoding.geocode_location", return_value=(None, None)):
                sync_parcel_from_17track(parcel, payload)
                sync_parcel_from_17track(parcel, payload)

        assert TrackingEvent.objects.filter(parcel=parcel).count() == 1

    def test_multiple_events_all_created(self, parcel):
        events = [
            {"a": "2026-05-01 10:00:00", "z": "Departed Shanghai", "c": "Shanghai", "d": "CN"},
            {"a": "2026-05-03 08:00:00", "z": "Transit Dubai", "c": "Dubai", "d": "AE"},
            {"a": "2026-05-05 14:00:00", "z": "Arrived Paris", "c": "Paris", "d": "FR"},
        ]
        payload = _make_payload(parcel.tracking_number, events=events)
        with patch("apps.tracking.tasks.geocode_event_then_simulate") as mock_task:
            mock_task.delay = MagicMock()
            with patch("apps.tracking.services.geocoding.geocode_location", return_value=(None, None)):
                sync_parcel_from_17track(parcel, payload)

        assert TrackingEvent.objects.filter(parcel=parcel).count() == 3

    def test_event_without_timestamp_and_description_skipped(self, parcel):
        """Events vides (pas de timestamp ni de description) doivent être ignorés."""
        events = [
            {"a": None, "z": "", "c": "", "d": ""},  # event vide
            {"a": "2026-05-01 10:00:00", "z": "Departed", "c": "Shanghai", "d": "CN"},
        ]
        payload = _make_payload(parcel.tracking_number, events=events)
        with patch("apps.tracking.tasks.geocode_event_then_simulate") as mock_task:
            mock_task.delay = MagicMock()
            with patch("apps.tracking.services.geocoding.geocode_location", return_value=(None, None)):
                sync_parcel_from_17track(parcel, payload)

        assert TrackingEvent.objects.filter(parcel=parcel).count() == 1

    def test_last_synced_at_updated(self, parcel):
        before = timezone.now()
        with patch("apps.tracking.tasks.geocode_event_then_simulate") as mock_task:
            mock_task.delay = MagicMock()
            with patch("apps.tracking.services.geocoding.geocode_location", return_value=(None, None)):
                result = sync_parcel_from_17track(parcel, _make_payload(parcel.tracking_number))
        assert result.last_synced_at >= before

    def test_flight_number_set_from_event(self, parcel):
        """Si un event a un numéro de vol extrait, parcel.flight_number doit être mis à jour."""
        events = [{
            "a": "2026-05-01 10:00:00",
            "z": "Departed on AF447 from CDG",
            "c": "Paris CDG",
            "d": "FR",
        }]
        payload = _make_payload(parcel.tracking_number, events=events)
        with patch("apps.tracking.tasks.geocode_event_then_simulate") as mock_task:
            mock_task.delay = MagicMock()
            with patch("apps.tracking.services.geocoding.geocode_location", return_value=(None, None)):
                result = sync_parcel_from_17track(parcel, payload)
        result.refresh_from_db()
        assert result.flight_number == "AF447"
