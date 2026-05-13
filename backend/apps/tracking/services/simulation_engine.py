"""SimulationEngine — calcule les segments de progression d'un colis.

Pour chaque paire d'events géocodés consécutifs, on estime :
  - estimated_departure  (timestamp du 1er event du segment)
  - estimated_arrival    (timestamp du 2ème event du segment)

Puis get_simulated_position() interpole la position actuelle par slerp
spherique (great-circle) selon (now - dep) / (arr - dep).
"""
import math
import logging
from django.utils import timezone
from apps.tracking.models import Parcel, TrackingEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Maths
# ---------------------------------------------------------------------------

def _slerp(lat1: float, lng1: float, lat2: float, lng2: float, t: float) -> tuple[float, float]:
    """Interpolation great-circle (slerp spherique) entre deux points GPS.
    t ∈ [0, 1]. Fallback linéaire si points trop proches.
    """
    t = max(0.0, min(1.0, t))

    def to_rad(v): return math.radians(v)
    def to_deg(v): return math.degrees(v)

    phi1, lam1 = to_rad(lat1), to_rad(lng1)
    phi2, lam2 = to_rad(lat2), to_rad(lng2)

    x1 = math.cos(phi1) * math.cos(lam1)
    y1 = math.cos(phi1) * math.sin(lam1)
    z1 = math.sin(phi1)

    x2 = math.cos(phi2) * math.cos(lam2)
    y2 = math.cos(phi2) * math.sin(lam2)
    z2 = math.sin(phi2)

    dot = x1 * x2 + y1 * y2 + z1 * z2
    dot = max(-1.0, min(1.0, dot))
    omega = math.acos(dot)

    if omega < 1e-10:
        # Points quasi-identiques → interpolation linéaire directe
        return (
            lat1 + (lat2 - lat1) * t,
            lng1 + (lng2 - lng1) * t,
        )

    sin_omega = math.sin(omega)
    s1 = math.sin((1.0 - t) * omega) / sin_omega
    s2 = math.sin(t * omega) / sin_omega

    x = s1 * x1 + s2 * x2
    y = s1 * y1 + s2 * y2
    z = s1 * z1 + s2 * z2

    lat = to_deg(math.atan2(z, math.sqrt(x * x + y * y)))
    lng = to_deg(math.atan2(y, x))
    return lat, lng


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Enrichissement des events (écrit estimated_departure / estimated_arrival)
# ---------------------------------------------------------------------------

def compute_parcel_simulation(parcel: Parcel) -> None:
    """Calcule et persiste estimated_departure / estimated_arrival sur chaque
    TrackingEvent géocodé du colis.

    Logique par paires d'events consécutifs (triés ASC timestamp) :
      event[i].estimated_departure = event[i].timestamp
      event[i].estimated_arrival   = event[i+1].timestamp
      event[-1].estimated_departure = event[-1].timestamp
      event[-1].estimated_arrival   = event[-1].timestamp  (destination finale)

    Les champs simulated=True sont posés sur tous les events traités.
    """
    geo_events = list(
        TrackingEvent.objects
        .filter(parcel=parcel, latitude__isnull=False, longitude__isnull=False)
        .order_by("timestamp")
    )

    if not geo_events:
        logger.debug(f"[SimEngine] {parcel.tracking_number}: aucun event géocodé, skip")
        return

    for i, ev in enumerate(geo_events):
        ev.estimated_departure = ev.timestamp
        if i + 1 < len(geo_events):
            ev.estimated_arrival = geo_events[i + 1].timestamp
        else:
            # Dernier event : on estime un delta de 0 (on est arrivé)
            ev.estimated_arrival = ev.timestamp
        ev.simulated = True
        ev.save(update_fields=["estimated_departure", "estimated_arrival", "simulated"])

    logger.info(
        f"[SimEngine] {parcel.tracking_number}: {len(geo_events)} segments calculés"
    )


# ---------------------------------------------------------------------------
# Calcul de position courante
# ---------------------------------------------------------------------------

def get_current_simulated_position(parcel: Parcel) -> dict | None:
    """Retourne la position simulée {lat, lng, progress, source, segment_index}
    en cherchant dans quel segment temporel on se trouve.

    Segments cherchés par ordre croissant ; on prend le premier segment
    dont now < estimated_arrival (on est encore en transit dessus).
    Si now > dernier arrival → on renvoie la destination finale.
    """
    now = timezone.now()

    segments = list(
        TrackingEvent.objects
        .filter(parcel=parcel, simulated=True, latitude__isnull=False)
        .order_by("timestamp")
    )

    if not segments:
        return None

    # Trouver le segment actif
    active = None
    active_idx = 0
    for i, ev in enumerate(segments):
        if ev.estimated_arrival is None:
            continue
        if now <= ev.estimated_arrival:
            active = ev
            active_idx = i
            break

    # Si on dépasse tous les segments → position du dernier event
    if active is None:
        last = segments[-1]
        return {
            "lat": last.latitude,
            "lng": last.longitude,
            "progress": 1.0,
            "source": "simulated",
            "segment_index": len(segments) - 1,
            "segment_total": len(segments),
        }

    dep_ts = active.estimated_departure
    arr_ts = active.estimated_arrival
    total_sec = (arr_ts - dep_ts).total_seconds() if arr_ts and dep_ts else 0

    if total_sec <= 0:
        t = 0.5
    else:
        t = (now - dep_ts).total_seconds() / total_sec
        t = max(0.05, min(0.95, t))

    # Destination du segment = prochain event ou même event
    if active_idx + 1 < len(segments):
        next_ev = segments[active_idx + 1]
        dest_lat, dest_lng = next_ev.latitude, next_ev.longitude
    else:
        dest_lat, dest_lng = active.latitude, active.longitude

    lat, lng = _slerp(active.latitude, active.longitude, dest_lat, dest_lng, t)

    # Progress globale = (segment_idx + t) / total_segments
    global_progress = round((active_idx + t) / max(len(segments), 1), 4)

    return {
        "lat": lat,
        "lng": lng,
        "progress": global_progress,
        "source": "simulated",
        "segment_index": active_idx,
        "segment_total": len(segments),
    }
