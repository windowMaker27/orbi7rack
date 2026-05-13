"""
Tests API — endpoints /api/parcels/
"""
import pytest
from unittest.mock import patch, MagicMock
from apps.tracking.models import Parcel, TrackingEvent


# ---------------------------------------------------------------------------
# GET /api/parcels/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestParcelList:
    def test_list_requires_auth(self, client):
        response = client.get("/api/parcels/")
        assert response.status_code == 401

    def test_list_empty(self, auth_client):
        response = auth_client.get("/api/parcels/")
        assert response.status_code == 200
        assert response.data["results"] == []

    def test_list_returns_own_parcels_only(self, auth_client, parcel, db, user):
        from django.contrib.auth import get_user_model
        other_user = get_user_model().objects.create_user(
            username="other", password="pass", email="other@test.com"
        )
        Parcel.objects.create(
            tracking_number="OTHER123",
            owner=other_user,
            status=Parcel.Status.PENDING,
        )
        response = auth_client.get("/api/parcels/")
        assert response.status_code == 200
        tracking_numbers = [p["tracking_number"] for p in response.data["results"]]
        assert "CNFR9010519938925HD" in tracking_numbers
        assert "OTHER123" not in tracking_numbers

    def test_list_parcel_fields(self, auth_client, parcel_with_events):
        response = auth_client.get("/api/parcels/")
        assert response.status_code == 200
        item = response.data["results"][0]
        for field in ["id", "tracking_number", "status", "origin_country",
                      "dest_country", "events", "estimated_position",
                      "origin_coords", "dest_coords"]:
            assert field in item, f"Champ manquant : {field}"

    def test_list_origin_coords_present(self, auth_client, parcel_with_events):
        response = auth_client.get("/api/parcels/")
        item = response.data["results"][0]
        assert item["origin_coords"] is not None
        assert "lat" in item["origin_coords"]
        assert "lng" in item["origin_coords"]

    def test_list_dest_coords_present(self, auth_client, parcel_with_events):
        response = auth_client.get("/api/parcels/")
        item = response.data["results"][0]
        assert item["dest_coords"] is not None

    def test_list_dest_coords_fallback_prefix(self, auth_client, parcel):
        """Sans events géocodés, dest_coords doit fallback sur CNFR → FR centroid."""
        response = auth_client.get("/api/parcels/")
        item = response.data["results"][0]
        assert item["dest_coords"] is not None
        dest = item["dest_coords"]
        assert abs(dest["lat"] - 46.22) < 1.0
        assert abs(dest["lng"] - 2.21) < 1.0


# ---------------------------------------------------------------------------
# GET /api/parcels/{id}/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestParcelDetail:
    def test_retrieve_own_parcel(self, auth_client, parcel):
        response = auth_client.get(f"/api/parcels/{parcel.id}/")
        assert response.status_code == 200
        assert response.data["tracking_number"] == parcel.tracking_number

    def test_cannot_retrieve_other_user_parcel(self, auth_client, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(
            username="other2", password="pass", email="other2@test.com"
        )
        other_parcel = Parcel.objects.create(
            tracking_number="USFR1234567890",
            owner=other,
            status=Parcel.Status.PENDING,
        )
        response = auth_client.get(f"/api/parcels/{other_parcel.id}/")
        assert response.status_code == 404

    def test_estimated_position_with_events(self, auth_client, parcel_with_events):
        from apps.tracking.services.simulation_engine import compute_parcel_simulation
        compute_parcel_simulation(parcel_with_events)
        response = auth_client.get(f"/api/parcels/{parcel_with_events.id}/")
        pos = response.data["estimated_position"]
        assert pos is not None
        assert "lat" in pos
        assert "lng" in pos
        assert "progress" in pos
        assert 0.0 <= pos["progress"] <= 1.0

    def test_estimated_position_no_events_fallback(self, auth_client, parcel):
        response = auth_client.get(f"/api/parcels/{parcel.id}/")
        pos = response.data["estimated_position"]
        assert pos is not None


# ---------------------------------------------------------------------------
# PATCH /api/parcels/{id}/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestParcelUpdate:
    def test_patch_description(self, auth_client, parcel):
        response = auth_client.patch(f"/api/parcels/{parcel.id}/", {
            "description": "Nouvelle description"
        })
        assert response.status_code == 200
        parcel.refresh_from_db()
        assert parcel.description == "Nouvelle description"

    def test_patch_cannot_change_status(self, auth_client, parcel):
        """status est read_only : un PATCH dessus doit être ignoré."""
        response = auth_client.patch(f"/api/parcels/{parcel.id}/", {
            "status": "delivered"
        })
        assert response.status_code == 200
        parcel.refresh_from_db()
        assert parcel.status == Parcel.Status.IN_TRANSIT  # inchangé

    def test_patch_other_user_parcel_returns_404(self, auth_client, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(
            username="other_patch", password="pass", email="op@test.com"
        )
        other_parcel = Parcel.objects.create(
            tracking_number="CNFR_OTHER_PATCH",
            owner=other,
            status=Parcel.Status.PENDING,
        )
        response = auth_client.patch(f"/api/parcels/{other_parcel.id}/", {
            "description": "hack"
        })
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/parcels/{id}/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestParcelDelete:
    def test_delete_own_parcel(self, auth_client, parcel):
        parcel_id = parcel.id
        response = auth_client.delete(f"/api/parcels/{parcel_id}/")
        assert response.status_code == 204
        assert not Parcel.objects.filter(id=parcel_id).exists()

    def test_deleted_parcel_returns_404(self, auth_client, parcel):
        parcel_id = parcel.id
        auth_client.delete(f"/api/parcels/{parcel_id}/")
        response = auth_client.get(f"/api/parcels/{parcel_id}/")
        assert response.status_code == 404

    def test_cannot_delete_other_user_parcel(self, auth_client, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(
            username="other_del", password="pass", email="od@test.com"
        )
        other_parcel = Parcel.objects.create(
            tracking_number="CNFR_OTHER_DEL",
            owner=other,
            status=Parcel.Status.PENDING,
        )
        response = auth_client.delete(f"/api/parcels/{other_parcel.id}/")
        assert response.status_code == 404
        assert Parcel.objects.filter(id=other_parcel.id).exists()  # toujours là


# ---------------------------------------------------------------------------
# GET /api/parcels/{id}/events/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestParcelEvents:
    def test_events_empty(self, auth_client, parcel):
        response = auth_client.get(f"/api/parcels/{parcel.id}/events/")
        assert response.status_code == 200
        assert response.data == []

    def test_events_returns_all(self, auth_client, parcel_with_events):
        response = auth_client.get(f"/api/parcels/{parcel_with_events.id}/events/")
        assert response.status_code == 200
        assert len(response.data) == 3

    def test_events_fields(self, auth_client, parcel_with_events):
        response = auth_client.get(f"/api/parcels/{parcel_with_events.id}/events/")
        event = response.data[0]
        for field in ["id", "timestamp", "location", "latitude", "longitude",
                      "status", "description", "transport_mode", "flight_iata",
                      "estimated_departure", "estimated_arrival", "simulated"]:
            assert field in event, f"Champ manquant dans event : {field}"

    def test_events_geo_coords_present(self, auth_client, parcel_with_events):
        response = auth_client.get(f"/api/parcels/{parcel_with_events.id}/events/")
        for event in response.data:
            assert event["latitude"] is not None
            assert event["longitude"] is not None


# ---------------------------------------------------------------------------
# POST /api/parcels/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestParcelCreate:
    def _mock_payload(self, tracking_number):
        return {
            "data": {
                "accepted": [{
                    "number": tracking_number,
                    "track": {
                        "e": 10, "b": 100, "d": 203, "w1": "La Poste",
                        "z1": [{
                            "a": "2026-05-01 10:00:00",
                            "z": "Departed from Shanghai",
                            "c": "Shanghai",
                            "d": "CN",
                        }],
                    }
                }]
            }
        }

    @patch("apps.api.views.SeventeentrackClient")
    def test_create_parcel_success(self, MockClient, auth_client):
        tracking_number = "CNFR0000000001TEST"
        mock_instance = MagicMock()
        mock_instance.register.return_value = None
        mock_instance.get_track_info.return_value = self._mock_payload(tracking_number)
        MockClient.return_value = mock_instance

        with patch("apps.tracking.services.geocoding.geocode_location", return_value=(31.23, 121.47)):
            response = auth_client.post("/api/parcels/", {
                "tracking_number": tracking_number,
                "description": "Test colis",
            })

        assert response.status_code == 201
        assert response.data["tracking_number"] == tracking_number
        assert response.data["status"] == "in_transit"
        assert Parcel.objects.filter(tracking_number=tracking_number).exists()

    @patch("apps.api.views.SeventeentrackClient")
    def test_create_duplicate_returns_400(self, MockClient, auth_client, parcel):
        mock_instance = MagicMock()
        mock_instance.register.return_value = None
        mock_instance.get_track_info.return_value = self._mock_payload(parcel.tracking_number)
        MockClient.return_value = mock_instance
        response = auth_client.post("/api/parcels/", {
            "tracking_number": parcel.tracking_number,
        })
        assert response.status_code == 400

    def test_create_requires_tracking_number(self, auth_client):
        response = auth_client.post("/api/parcels/", {})
        assert response.status_code == 400
