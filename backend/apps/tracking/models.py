import math
from django.db import models
from django.conf import settings


class Parcel(models.Model):
    class Status(models.TextChoices):
        PENDING     = 'pending',     'En attente'
        IN_TRANSIT  = 'in_transit',  'En transit'
        OUT_FOR_DEL = 'out_for_delivery', 'En livraison'
        DELIVERED   = 'delivered',   'Livré'
        EXCEPTION   = 'exception',   'Incident'
        EXPIRED     = 'expired',     'Expiré'

    tracking_number = models.CharField(max_length=100, unique=True)
    carrier         = models.CharField(max_length=100, blank=True)
    description     = models.CharField(max_length=255, blank=True)
    origin_country  = models.CharField(max_length=100, blank=True)
    dest_country    = models.CharField(max_length=100, blank=True)
    status          = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    owner           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parcels')
    last_synced_at  = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    flight_number   = models.CharField(max_length=20, blank=True, null=True,
                                       help_text="Ex: AF447, pour liaison FlightRadar")

    # Dernière position live persistée
    last_live_lat   = models.FloatField(null=True, blank=True)
    last_live_lng   = models.FloatField(null=True, blank=True)
    last_live_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.tracking_number} ({self.get_status_display()})'


class TrackingEvent(models.Model):
    class TransportMode(models.TextChoices):
        AIR     = 'air',     'Aérien'
        ROAD    = 'road',    'Terrestre'
        SEA     = 'sea',     'Maritime'
        UNKNOWN = 'unknown', 'Inconnu'

    parcel         = models.ForeignKey(Parcel, related_name='events', on_delete=models.CASCADE)
    timestamp      = models.DateTimeField()
    location       = models.CharField(max_length=255, blank=True)
    latitude       = models.FloatField(null=True, blank=True)
    longitude      = models.FloatField(null=True, blank=True)
    status         = models.CharField(max_length=100)
    description    = models.TextField(blank=True)
    raw_data       = models.JSONField(default=dict, blank=True)

    # Étape 1 — extraction vol
    flight_iata    = models.CharField(
        max_length=10, blank=True, null=True,
        help_text="Code IATA du vol extrait (ex: UA123, AF447)"
    )
    transport_mode = models.CharField(
        max_length=20,
        choices=TransportMode.choices,
        default=TransportMode.UNKNOWN,
        blank=True,
        help_text="Mode de transport détecté pour cet événement"
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.parcel.tracking_number} — {self.status} @ {self.location}'
