"""
seed_demo.py — Crée des colis de démo liés à des vols live (FlightRadar).

Usage (depuis /backend) :
  docker compose exec backend python scripts/seed_demo.py --flight AF011
  docker compose exec backend python scripts/seed_demo.py --flight AF011 --username monuser
  docker compose exec backend python scripts/seed_demo.py --flight AF011 --tracking DEMO-AF011-001 --description "Mon colis Air France"

Arguments :
  --flight      OBLIGATOIRE. Numéro de vol IATA (ex: AF011, UA123).
  --username    Attache le colis à un user existant (défaut: user 'demo').
  --tracking    Numéro de tracking custom (défaut: généré depuis le vol).
  --description Description du colis (défaut: "Colis démo <flight>").
  --carrier     Transporteur (défaut: extrait du préfixe IATA du vol).
  --origin      Pays d'origine ISO (ex: US). Optionnel.
  --dest        Pays de destination ISO (ex: FR). Optionnel.
  --force       Supprime le colis existant avec ce tracking_number et le recrée.
"""
import os
import sys
import argparse
import django
from pathlib import Path

# --- Bootstrap Django ---
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.tracking.models import Parcel

User = get_user_model()

# Mapping préfixe IATA → nom de compagnie (quick lookup)
IATA_CARRIERS = {
    "AF": "Air France",
    "UA": "United Airlines",
    "AA": "American Airlines",
    "BA": "British Airways",
    "LH": "Lufthansa",
    "EK": "Emirates",
    "QR": "Qatar Airways",
    "DL": "Delta Air Lines",
    "KL": "KLM",
    "IB": "Iberia",
    "TK": "Turkish Airlines",
    "SQ": "Singapore Airlines",
    "CX": "Cathay Pacific",
    "NH": "ANA",
    "JL": "Japan Airlines",
    "CA": "Air China",
    "MU": "China Eastern",
    "CZ": "China Southern",
    "KE": "Korean Air",
    "OZ": "Asiana Airlines",
}


def guess_carrier(flight_number: str) -> str:
    prefix = "".join(c for c in flight_number if c.isalpha()).upper()
    return IATA_CARRIERS.get(prefix, prefix or "Unknown")


def get_or_create_demo_user() -> object:
    user, created = User.objects.get_or_create(
        username="demo",
        defaults={"email": "demo@orbi7rack.local"},
    )
    if created:
        user.set_password("demo1234")
        user.save()
        print("[seed] User 'demo' créé (password: demo1234)")
    else:
        print("[seed] User 'demo' existant")
    return user


def run(
    flight_number: str,
    target_username: str | None = None,
    tracking_number: str | None = None,
    description: str | None = None,
    carrier: str | None = None,
    origin_country: str | None = None,
    dest_country: str | None = None,
    force: bool = False,
):
    flight_number = flight_number.strip().upper()

    # --- Résolution du user ---
    if target_username:
        try:
            user = User.objects.get(username=target_username)
            print(f"[seed] User '{target_username}' trouvé (id={user.pk})")
        except User.DoesNotExist:
            print(f"[seed] ERREUR : user '{target_username}' introuvable. Annulation.")
            sys.exit(1)
    else:
        user = get_or_create_demo_user()

    # --- Valeurs par défaut ---
    tracking = tracking_number or f"DEMO-{flight_number}-001"
    desc = description or f"Colis démo {flight_number}"
    car = carrier or guess_carrier(flight_number)

    # --- Gestion de l'existant ---
    existing = Parcel.objects.filter(tracking_number=tracking).first()
    if existing:
        if force:
            print(f"[seed] --force : suppression de '{tracking}'...")
            existing.delete()
        else:
            print(
                f"[seed] Le colis '{tracking}' existe déjà (owner={existing.owner.username}). "
                f"Utilisez --force pour le recréer."
            )
            sys.exit(0)

    # --- Création du colis ---
    parcel = Parcel.objects.create(
        tracking_number=tracking,
        carrier=car,
        description=desc,
        origin_country=origin_country or "",
        dest_country=dest_country or "",
        status=Parcel.Status.IN_TRANSIT,
        owner=user,
        flight_number=flight_number,
    )

    print(
        f"[seed] ✓ Colis '{parcel.tracking_number}' créé pour '{user.username}'\n"
        f"         → vol live : {flight_number}\n"
        f"         → carrier  : {car}\n"
        f"         → status   : {parcel.get_status_display()}"
    )
    print("[seed] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed colis démo avec vol live — Orbi7rack")
    parser.add_argument("--flight",      required=True,  help="Numéro de vol IATA (ex: AF011)")
    parser.add_argument("--username",    default=None,   help="Username du compte cible (défaut: 'demo')")
    parser.add_argument("--tracking",    default=None,   help="Numéro de tracking custom")
    parser.add_argument("--description", default=None,   help="Description du colis")
    parser.add_argument("--carrier",     default=None,   help="Nom du transporteur")
    parser.add_argument("--origin",      default=None,   help="Pays d'origine ISO (ex: US)")
    parser.add_argument("--dest",        default=None,   help="Pays de destination ISO (ex: FR)")
    parser.add_argument("--force",       action="store_true", help="Supprime et recrée si le tracking existe déjà")
    args = parser.parse_args()

    run(
        flight_number=args.flight,
        target_username=args.username,
        tracking_number=args.tracking,
        description=args.description,
        carrier=args.carrier,
        origin_country=args.origin,
        dest_country=args.dest,
        force=args.force,
    )
