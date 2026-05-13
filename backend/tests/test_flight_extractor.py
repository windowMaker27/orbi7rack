"""
Tests unitaires — flight_extractor.py
Aucun appel réseau (AviationStack mocké).
"""
import pytest
from apps.tracking.services.flight_extractor import (
    extract_flight_number,
    detect_transport_mode,
    _resolve_carrier_iata,
    enrich_event_flight,
)


# ---------------------------------------------------------------------------
# extract_flight_number
# ---------------------------------------------------------------------------

class TestExtractFlightNumber:
    def test_simple_iata_code(self):
        assert extract_flight_number("Flight AF447 departed") == "AF447"

    def test_with_space(self):
        result = extract_flight_number("Vol AF 447 au départ de CDG")
        assert result == "AF447"

    def test_cargo_code_5x(self):
        assert extract_flight_number("Loaded onto 5X9999") == "5X9999"

    def test_three_letter_prefix(self):
        assert extract_flight_number("DHL DI9876 cargo") == "DI9876"

    def test_no_match_returns_none(self):
        assert extract_flight_number("Colis en transit") is None

    def test_empty_string_returns_none(self):
        assert extract_flight_number("") is None

    def test_false_positive_pure_digit_prefix_ignored(self):
        """Un préfixe tout numérique ne doit pas matcher (ex: code postal)."""
        result = extract_flight_number("Zone 75 1234 distribution")
        # '75' est purement numérique → doit être ignoré
        assert result is None

    def test_location_used_as_context(self):
        result = extract_flight_number("", location="UA123 gate B")
        assert result == "UA123"

    def test_short_flight_number(self):
        assert extract_flight_number("KL123 Amsterdam") == "KL123"

    def test_four_digit_flight(self):
        assert extract_flight_number("EK1234 from Dubai") == "EK1234"


# ---------------------------------------------------------------------------
# detect_transport_mode
# ---------------------------------------------------------------------------

class TestDetectTransportMode:
    def test_flight_keyword(self):
        assert detect_transport_mode("flight departed from Shanghai", "") == "air"

    def test_airport_keyword(self):
        assert detect_transport_mode("Arrived at airport", "") == "air"

    def test_road_keyword_truck(self):
        assert detect_transport_mode("Loaded on truck for delivery", "") == "road"

    def test_road_keyword_hub(self):
        assert detect_transport_mode("", "sorting center Roissy") == "road"

    def test_sea_keyword(self):
        assert detect_transport_mode("Loaded on vessel at port", "") == "sea"

    def test_unknown_default(self):
        assert detect_transport_mode("Colis reçu", "France") == "unknown"

    def test_flight_takes_priority_over_road(self):
        """Si les deux keywords sont présents, air a priorité."""
        result = detect_transport_mode("flight loaded on truck", "")
        assert result == "air"

    def test_customs_keyword_is_air(self):
        assert detect_transport_mode("Customs clearance at CDG", "") == "air"

    def test_iata_flight_code_in_description(self):
        """Un code de vol dans la description → air par défaut."""
        result = detect_transport_mode("AF447", "")
        assert result == "air"


# ---------------------------------------------------------------------------
# _resolve_carrier_iata
# ---------------------------------------------------------------------------

class TestResolveCarrierIata:
    def test_ups_resolves(self):
        assert _resolve_carrier_iata("ups") == "5X"

    def test_fedex_resolves(self):
        assert _resolve_carrier_iata("fedex") == "FX"

    def test_dhl_resolves(self):
        assert _resolve_carrier_iata("dhl") == "D0"

    def test_case_insensitive(self):
        assert _resolve_carrier_iata("UPS") == "5X"
        assert _resolve_carrier_iata("FedEx") == "FX"

    def test_partial_match(self):
        """'air france cargo' doit matcher 'air france'."""
        result = _resolve_carrier_iata("air france cargo")
        assert result == "AF"

    def test_unknown_carrier_returns_none(self):
        assert _resolve_carrier_iata("XYZ Carrier Inconnu") is None

    def test_empty_string_returns_none(self):
        assert _resolve_carrier_iata("") is None


# ---------------------------------------------------------------------------
# enrich_event_flight
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnrichEventFlight:
    def _make_event(self, description, location=""):
        """Crée un TrackingEvent en mémoire (non persisté) pour les tests."""
        from django.utils import timezone
        from apps.tracking.models import Parcel, TrackingEvent
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username="ev_user", password="pass", email="ev@test.com"
        )
        parcel = Parcel.objects.create(
            tracking_number="TEST0001",
            owner=user,
            status=Parcel.Status.IN_TRANSIT,
        )
        event = TrackingEvent(
            parcel=parcel,
            timestamp=timezone.now(),
            description=description,
            location=location,
            status="in_transit",
        )
        return event

    def test_flight_found_sets_flight_iata(self):
        event = self._make_event("Departed on AF447 from CDG")
        result = enrich_event_flight(event)
        assert result is True
        assert event.flight_iata == "AF447"
        assert event.transport_mode == "air"

    def test_road_event_no_flight(self):
        event = self._make_event("Colis en transit hub sorting center")
        result = enrich_event_flight(event)
        assert result is False
        assert event.flight_iata is None
        assert event.transport_mode == "road"

    def test_unknown_event(self):
        event = self._make_event("Colis reçu en entrepôt")
        result = enrich_event_flight(event)
        assert result is False

    def test_aviationstack_not_called_without_key(self):
        """Sans API key, le fallback AviationStack ne doit pas être appelé."""
        from unittest.mock import patch
        event = self._make_event("vol departed airport CDG")  # mode=air, pas de numéro
        with patch("apps.tracking.services.flight_extractor.requests.get") as mock_get:
            enrich_event_flight(event, carrier_name="Air France", dep_iata="CDG")
            # AVIATIONSTACK_API_KEY est vide en test → requests.get ne doit pas être appelé
            mock_get.assert_not_called()
