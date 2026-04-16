from django.contrib import admin
from .models import Parcel, TrackingEvent


@admin.register(Parcel)
class ParcelAdmin(admin.ModelAdmin):
    list_display  = ('tracking_number', 'carrier', 'status', 'owner', 'updated_at')
    list_filter   = ('status', 'carrier')
    search_fields = ('tracking_number', 'description')


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display  = ('parcel', 'status', 'location', 'timestamp')
    list_filter   = ('status',)
