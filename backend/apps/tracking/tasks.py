from celery import shared_task
from django.utils import timezone
from apps.tracking.models import Parcel, TrackingEvent
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


@shared_task
def run_simulation_for_parcel(parcel_id: int):
    """Calcule les segments SimulationEngine pour un colis.
    Déclenché après geocodage ou refresh.
    """
    try:
        parcel = Parcel.objects.get(id=parcel_id)
    except Parcel.DoesNotExist:
        return

    from apps.tracking.services.simulation_engine import compute_parcel_simulation
    compute_parcel_simulation(parcel)


@shared_task
def geocode_event_then_simulate(event_id: int):
    """Géocode un event puis déclenche le SimulationEngine sur son colis.
    Remplace l'ancien geocode_event dans la chaîne parser → tasks.
    """
    from apps.tracking.services.geocoding import geocode_location
    from apps.tracking.services.simulation_engine import compute_parcel_simulation

    try:
        event = TrackingEvent.objects.get(id=event_id)
    except TrackingEvent.DoesNotExist:
        return

    if event.location and not event.latitude:
        lat, lng = geocode_location(event.location)
        if lat:
            event.latitude = lat
            event.longitude = lng
            event.save(update_fields=["latitude", "longitude"])

    # Recalcule les segments de tout le colis après chaque geocodage
    compute_parcel_simulation(event.parcel)
