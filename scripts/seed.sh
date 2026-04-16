#!/usr/bin/env bash
# Insère des données de démo dans la base
set -e

echo "🌱 Seeding demo data..."
docker compose exec backend python manage.py shell <<'EOF'
from apps.users.models import User
from apps.tracking.models import Parcel, TrackingEvent
from django.utils import timezone
from datetime import timedelta

# Utilisateur démo
user, _ = User.objects.get_or_create(
    email='demo@orbi7rack.dev',
    defaults={'username': 'demo', 'is_active': True}
)
user.set_password('demo1234')
user.save()

# Colis démo
parcels = [
    {'tracking_number': 'JT014080058CN', 'carrier': 'China Post', 'description': 'Composants électroniques', 'origin_country': 'CN', 'dest_country': 'FR', 'status': 'in_transit'},
    {'tracking_number': 'LY123456789CN', 'carrier': 'Cainiao', 'description': 'Accessoires gaming', 'origin_country': 'CN', 'dest_country': 'FR', 'status': 'out_for_delivery'},
    {'tracking_number': '1Z999AA10123456784', 'carrier': 'UPS', 'description': 'Livre technique', 'origin_country': 'US', 'dest_country': 'FR', 'status': 'delivered'},
]

for p in parcels:
    parcel, _ = Parcel.objects.get_or_create(tracking_number=p['tracking_number'], defaults={**p, 'owner': user})
    print(f'  ✓ {parcel}')

print('✅ Seed terminé — demo@orbi7rack.dev / demo1234')
EOF
