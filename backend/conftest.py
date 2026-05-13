"""
conftest.py — fixtures globales pytest-django
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.tracking.models import Parcel, TrackingEvent

User = get_user_model()


@pytest.fixture(autouse=True)
def suppress_jwt_key_warnings():
    """Supprime InsecureKeyLengthWarning due à la SECRET_KEY courte en test."""
    import warnings
    from jwt.exceptions import InsecureKeyLengthWarning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InsecureKeyLengthWarning)
        yield


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        email="test@example.com",
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def parcel(user):
    return Parcel.objects.create(
        tracking_number="CNFR9010519938925HD",
        owner=user,
        origin_country="CN",
        dest_country="FR",
        status=Parcel.Status.IN_TRANSIT,
    )


@pytest.fixture
def parcel_with_events(user):
    p = Parcel.objects.create(
        tracking_number="CNFR9010519938925HD",
        owner=user,
        origin_country="CN",
        dest_country="FR",
        status=Parcel.Status.IN_TRANSIT,
    )
    now = timezone.now()
    TrackingEvent.objects.create(
        parcel=p,
        timestamp=now - timedelta(days=10),
        location="Shanghai, CN",
        latitude=31.23,
        longitude=121.47,
        status="Departed",
        description="Colis parti de Shanghai",
    )
    TrackingEvent.objects.create(
        parcel=p,
        timestamp=now - timedelta(days=5),
        location="Dubai, AE",
        latitude=25.20,
        longitude=55.27,
        status="In transit",
        description="Transit Dubai",
    )
    TrackingEvent.objects.create(
        parcel=p,
        timestamp=now - timedelta(days=1),
        location="Paris CDG, FR",
        latitude=48.85,
        longitude=2.35,
        status="Arrived",
        description="Arrivé Paris CDG",
    )
    return p
