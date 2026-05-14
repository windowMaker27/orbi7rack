import re

from datetime import datetime
from typing import Any

from django.utils import timezone
from datetime import timezone as dt_timezone

from apps.tracking.models import Parcel, TrackingEvent
from apps.tracking.services.geocoding import country_code_to_iso, geocode_location
from apps.tracking.services.flight_extractor import enrich_event_flight

STATUS_MAP = {
    0: Parcel.Status.PENDING,
    10: Parcel.Status.IN_TRANSIT,
    20: Parcel.Status.EXPIRED,
    30: Parcel.Status.OUT_FOR_DEL,
    35: Parcel.Status.EXCEPTION,
    40: Parcel.Status.DELIVERED,
    50: Parcel.Status.EXCEPTION,
}

# Préfixes de tracking number → pays destination ISO2
_TRACKING_PREFIX_DEST = {
    "CNFR": "FR", "CNDE": "DE", "CNGB": "GB", "CNUS": "US",
    "CNPL": "PL", "CNNL": "NL", "CNES": "ES", "CNIT": "IT",
    "CNBE": "BE", "CNPT": "PT", "CNSE": "SE", "CNCH": "CH",
    "CNAT": "AT", "CNCA": "CA", "CNAU": "AU", "CNJP": "JP",
    "CNKR": "KR", "CNSG": "SG", "CNHK": "HK",
}

# Préfixes de tracking number → pays origine ISO2
_TRACKING_PREFIX_ORIGIN = {
    "CN": "CN",  # tous les CNFR, CNDE… viennent de Chine
    "US": "US",
    "GB": "GB",
    "DE": "DE",
    "FR": "FR",
}


def _resolve_country_from_prefix(tracking_number: str) -> tuple[str, str]:
    """Retourne (origin_iso, dest_iso) depuis le préfixe du numéro de suivi."""
    tn = (tracking_number or "").upper()
    dest = ""
    for prefix, country in _TRACKING_PREFIX_DEST.items():
        if tn.startswith(prefix):
            dest = country
            break
    # Origine : les 2 premiers caractères s'ils sont dans la table
    origin = _TRACKING_PREFIX_ORIGIN.get(tn[:2], "")
    return origin, dest


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
    parts = [event.get("c", "").strip(), event.get("d", "").strip()]
    location = ", ".join([p for p in parts if p])
    if location:
        return location

    description = event.get("z", "")
    match = re.match(r"^\[([^\]]+)\]", description)
    if match:
        return match.group(1)

    return ""


def sync_parcel_from_17track(parcel: Parcel, payload: dict[str, Any]) -> Parcel:
    import logging
    logger = logging.getLogger(__name__)

    accepted = payload.get("data", {}).get("accepted", [])
    if not accepted:
        raise ValueError("Aucun suivi disponible sur 17TRACK.")

    item = accepted[0]
    track = item.get("track", {})

    origin_code = track.get("b") or 0
    dest_code   = track.get("d") or 0

    iso_origin, _, _, _ = country_code_to_iso(origin_code)
    iso_dest, _, _, _   = country_code_to_iso(dest_code)

    # Fallback préfixe tracking number si 17track ne fournit pas les pays
    prefix_origin, prefix_dest = _resolve_country_from_prefix(parcel.tracking_number)

    # origin_country : ne pas écraser si déjà défini (17track change de pays au fil des étapes)
    if not parcel.origin_country:
        parcel.origin_country = iso_origin or prefix_origin or str(origin_code)

    # dest_country : 17track > fallback préfixe > conserver existant
    if iso_dest:
        parcel.dest_country = iso_dest
    elif not parcel.dest_country and prefix_dest:
        parcel.dest_country = prefix_dest
        logger.info(
            f"[parser] dest_country résolu via préfixe pour {parcel.tracking_number} → {prefix_dest}"
        )
    elif not parcel.dest_country:
        logger.warning(
            f"[parser] dest_country introuvable pour {parcel.tracking_number} (d={dest_code})"
        )

    parcel.status         = STATUS_MAP.get(track.get("e"), Parcel.Status.PENDING)
    parcel.carrier        = str(track.get("w1") or parcel.carrier or "")
    parcel.last_synced_at = timezone.now()
    parcel.save()

    from apps.tracking.services.flight_extractor import _resolve_carrier_iata
    carrier_iata_prefix = _resolve_carrier_iata(parcel.carrier or "")

    events = track.get("z1", []) or []
    created_event_ids = []

    for event in events:
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

        if created:
            enrich_event_flight(
                event_obj,
                carrier_name=parcel.carrier or "",
            )
            event_obj.save(update_fields=["flight_iata", "transport_mode"])

            if location:
                created_event_ids.append(event_obj.id)

        if event_obj.flight_iata and not parcel.flight_number:
            parcel.flight_number = event_obj.flight_iata
            parcel.save(update_fields=["flight_number"])

    from apps.tracking.tasks import geocode_event_then_simulate
    for event_id in created_event_ids:
        geocode_event_then_simulate.delay(event_id)

    return parcel
