import re

from datetime import datetime
from typing import Any

from django.utils import timezone
from datetime import timezone as dt_timezone

from apps.tracking.models import Parcel, TrackingEvent
from apps.tracking.services.geocoding import country_code_to_iso, geocode_event

STATUS_MAP = {
    0: Parcel.Status.PENDING,
    10: Parcel.Status.IN_TRANSIT,
    20: Parcel.Status.EXPIRED,
    30: Parcel.Status.OUT_FOR_DEL,
    35: Parcel.Status.EXCEPTION,
    40: Parcel.Status.DELIVERED,
    50: Parcel.Status.EXCEPTION,
}


def parse_17track_datetime(value: str | None):
    if not value:
        return None

    value = value.strip()
    formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")

    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return timezone.make_aware(dt, dt_timezone.utc)
        except ValueError:
            continue

    return None



def extract_event_location(event: dict[str, Any]) -> str:
    # Priorité : champs c et d
    parts = [event.get("c", "").strip(), event.get("d", "").strip()]
    location = ", ".join([p for p in parts if p])
    if location:
        return location

    # Fallback : extrait [Lieu] depuis le champ z
    description = event.get("z", "")
    match = re.match(r"^\[([^\]]+)\]", description)
    if match:
        return match.group(1)

    return ""


def sync_parcel_from_17track(parcel: Parcel, payload: dict[str, Any]) -> Parcel:
    accepted = payload.get("data", {}).get("accepted", [])
    if not accepted:
        raise ValueError("Aucun suivi disponible sur 17TRACK.")

    item = accepted[0]
    track = item.get("track", {})
    print("TRACK KEYS:", list(track.keys()))   
    print("Z1 VALUE:", track.get("z1", "ABSENT"))  

    # Mapper origin/dest country
    origin_code = track.get("b") or 0
    dest_code = track.get("c") or 0
    iso_origin, _, _, _ = country_code_to_iso(origin_code)
    iso_dest, _, _, _   = country_code_to_iso(dest_code)

    parcel.status         = STATUS_MAP.get(track.get("e"), Parcel.Status.PENDING)
    parcel.origin_country = iso_origin or str(origin_code)
    parcel.dest_country   = iso_dest   or str(dest_code)
    parcel.carrier        = str(track.get("w1") or parcel.carrier or "")
    parcel.last_synced_at = timezone.now()
    parcel.save()

    events = track.get("z1", []) or []
    for event in events:
        print("RAW EVENT:", event)
        timestamp   = parse_17track_datetime(event.get("a"))
        description = (event.get("z") or event.get("ps") or "").strip()
        location    = extract_event_location(event)

        if not timestamp and not description:
            continue

        event_obj, created = TrackingEvent.objects.get_or_create(  # ← DANS la boucle
            parcel=parcel,
            timestamp=timestamp or timezone.now(),
            description=description,
            defaults={
                "location":  location,
                "latitude":  None,
                "longitude": None,
                "status":    description[:100] if description else "Inconnu",
            },
        )

        if created and location:
            geocode_event.delay(event_obj.id)  # ← aussi DANS la boucle

    return parcel