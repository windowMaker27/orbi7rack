from celery import shared_task
from django.utils import timezone
from apps.tracking.models import Parcel
from apps.tracking.services.parser import sync_parcel_from_17track
from apps.tracking.services.seventeentrack import SeventeentrackClient


@shared_task
def refresh_all_parcels():
    """Rafraîchit tous les colis non livrés."""
    parcels = Parcel.objects.exclude(status=Parcel.Status.DELIVERED)
    client = SeventeentrackClient()

    for parcel in parcels:
        try:
            payload = client.get_track_info(parcel.tracking_number)
            sync_parcel_from_17track(parcel, payload)
        except Exception as e:
            print(f"Erreur refresh {parcel.tracking_number}: {e}")