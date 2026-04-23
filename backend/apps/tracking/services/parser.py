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
    # "b" = pays d'origine, "d" = pays de destination finale
    # ATTENTION : "c" = pays de transit ACTUEL (ne pas utiliser pour dest_country)
    origin_code = track.get("b") or 0
    dest_code   = track.get("d") or 0

    # Si "d" absent (ancien format), fallback sur le dernier event geocodé
    # pour éviter d'utiliser "c" (transit courant) comme destination
    if not dest_code:
        import logging
        logging.getLogger(__name__).warning(
            f"[17track] Champ 'd' absent pour {parcel.tracking_number}, dest_country non mis à jour"
        )

    iso_origin, _, _, _ = country_code_to_iso(origin_code)
    iso_dest, _, _, _   = country_code_to_iso(dest_code)

    parcel.status         = STATUS_MAP.get(track.get("e"), Parcel.Status.PENDING)
    parcel.origin_country = iso_origin or str(origin_code)
    # Ne met à jour dest_country que si on a une vraie destination finale
    if iso_dest:
        parcel.dest_country = iso_dest
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

        event_obj, created = TrackingEvent.objects.get_or_create(
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
            geocode_event.delay(event_obj.id)

    return parcel
