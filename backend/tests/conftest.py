"""
conftest.py — fixtures partagées + override settings pour les tests.

Overrides critiques :
  - SQLite en mémoire (pas besoin de PostgreSQL)
  - Celery en mode eager (tasks synchrones)
  - Clés API vides (pas d'appels réseau réels)
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def pytest_configure(config):
    settings.DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.SEVENTEENTRACK_API_KEY = "dummy"
    settings.AVIATIONSTACK_API_KEY = ""
    settings.OPENSKY_USER = ""
    settings.OPENSKY_PASS = ""


User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        email="test@orbi7rack.test",
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def parcel(db, user):
    from apps.tracking.models import Parcel
    return Parcel.objects.create(
        tracking_number="CNFR9010519938925HD",
        carrier="La Poste",
        description="Colis test",
        origin_country="CN",
        dest_country="FR",
        status=Parcel.Status.IN_TRANSIT,
        owner=user,
    )


@pytest.fixture
def parcel_with_events(db, parcel):
    """Colis avec 3 events géocodés sur une route CN → FR."""
    from apps.tracking.models import TrackingEvent
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()

    events_data = [
        # Shanghai
        dict(timestamp=now - timedelta(days=10), location="Shanghai, CN",
             latitude=31.23, longitude=121.47, status="Departed",
             description="Departed from origin facility"),
        # Dubai hub
        dict(timestamp=now - timedelta(days=5), location="Dubai, AE",
             latitude=25.20, longitude=55.27, status="In transit",
             description="flight departed"),
        # Paris CDG
        dict(timestamp=now - timedelta(days=1), location="Paris, FR",
             latitude=48.85, longitude=2.35, status="Arrived",
             description="Arrived at destination country"),
    ]

    for i, data in enumerate(events_data):
        TrackingEvent.objects.create(parcel=parcel, **data)

    return parcel
