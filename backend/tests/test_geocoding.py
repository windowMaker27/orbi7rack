"""
Tests unitaires — geocoding.py
Pas d'appel réseau réel : Nominatim est mocké.
"""
import pytest
from unittest.mock import patch, MagicMock
from apps.tracking.services.geocoding import geocode_location, country_code_to_iso


# ---------------------------------------------------------------------------
# country_code_to_iso
# ---------------------------------------------------------------------------

class TestCountryCodeToIso:
    def test_known_code_china(self):
        iso, lat, lng, name = country_code_to_iso(100)
        assert iso == "CN"
        assert abs(lat - 35.86) < 0.01
        assert abs(lng - 104.19) < 0.01

    def test_known_code_france(self):
        iso, lat, lng, name = country_code_to_iso(203)
        assert iso == "FR"

    def test_unknown_code_returns_empty(self):
        iso, lat, lng, name = country_code_to_iso(9999)
        assert iso == ""
        assert lat is None
        assert lng is None

    def test_zero_code_returns_empty(self):
        iso, lat, lng, name = country_code_to_iso(0)
        assert iso == ""

    def test_string_code_is_coerced(self):
        """Les codes peuvent arriver comme string depuis 17track."""
        iso, lat, lng, name = country_code_to_iso("100")
        assert iso == "CN"

    def test_invalid_string_returns_empty(self):
        iso, lat, lng, name = country_code_to_iso("abc")
        assert iso == ""

    def test_none_returns_empty(self):
        iso, lat, lng, name = country_code_to_iso(None)
        assert iso == ""

    def test_duplicate_605_is_france(self):
        """Code 605 est un alias FR (Outre-mer)."""
        iso, _, _, _ = country_code_to_iso(605)
        assert iso == "FR"


# ---------------------------------------------------------------------------
# geocode_location
# ---------------------------------------------------------------------------

class TestGeocodeLocation:
    def test_empty_string_returns_none(self):
        lat, lng = geocode_location("")
        assert lat is None
        assert lng is None

    def test_whitespace_returns_none(self):
        lat, lng = geocode_location("   ")
        assert lat is None
        assert lng is None

    def test_none_returns_none(self):
        lat, lng = geocode_location(None)
        assert lat is None
        assert lng is None

    def test_successful_geocode(self):
        mock_result = MagicMock()
        mock_result.latitude = 48.8566
        mock_result.longitude = 2.3522

        with patch("apps.tracking.services.geocoding._geolocator") as mock_geo:
            mock_geo.geocode.return_value = mock_result
            lat, lng = geocode_location("Paris, France")

        assert lat == pytest.approx(48.8566)
        assert lng == pytest.approx(2.3522)

    def test_unknown_location_returns_none(self):
        with patch("apps.tracking.services.geocoding._geolocator") as mock_geo:
            mock_geo.geocode.return_value = None
            lat, lng = geocode_location("xyzxyz_lieu_inexistant")

        assert lat is None
        assert lng is None

    def test_timeout_retries_then_returns_none(self):
        from geopy.exc import GeocoderTimedOut

        with patch("apps.tracking.services.geocoding._geolocator") as mock_geo:
            with patch("apps.tracking.services.geocoding.time.sleep"):
                mock_geo.geocode.side_effect = GeocoderTimedOut()
                lat, lng = geocode_location("Paris", retries=2)

        assert lat is None
        assert lng is None
        assert mock_geo.geocode.call_count == 2  # 2 tentatives

    def test_unavailable_returns_none(self):
        from geopy.exc import GeocoderUnavailable

        with patch("apps.tracking.services.geocoding._geolocator") as mock_geo:
            mock_geo.geocode.side_effect = GeocoderUnavailable()
            lat, lng = geocode_location("Tokyo")

        assert lat is None
        assert lng is None
