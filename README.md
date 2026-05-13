# Orbi7rack 🌐

> Suivi de colis réinventé — globe 3D holographique, mises à jour en temps réel, simulation de trajectoire.

<!-- SCREENSHOT : hero — globe en mode sombre avec 2-3 arcs de vol actifs et sidebar ouverte -->
<!-- [ insérer captures/demo-globe.png ] -->

---

## Features

- 🌍 **Globe 3D interactif** (Three.js via `globe.gl`) avec arcs de vol animés et marqueurs de position
- ✈️ **SimulationEngine** — reconstruit la trajectoire géographique d'un colis à partir de ses events (haversine + slerp, détection air/road/sea)
- 📡 **Sync 17TRACK** — récupère et parse les events de tracking en temps réel via Celery
- 🔐 **Auth JWT** — inscription / connexion, tokens access + refresh
- 🌗 **Light / Dark mode** intégré

---

## Stack

| Couche | Techno |
|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Globe | `globe.gl` (Three.js) |
| Backend | Django 5 + Django REST Framework |
| Auth | SimpleJWT |
| Base de données | PostgreSQL 16 |
| Queue / Scheduler | Celery + Redis + Celery Beat |
| Tracking API | [17TRACK](https://api.17track.net) |
| Géocodage | Nominatim (OpenStreetMap) |
| Infra | Docker Compose + Makefile |

---

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.20
- Une clé API [17TRACK](https://api.17track.net)

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/windowMaker27/orbi7rack.git
cd orbi7rack

# 2. Configure
cp .env.example .env
# Remplis les variables obligatoires (voir section Variables d'environnement)

# 3. Build & start
make build
make up
make migrate

# 4. (Optionnel) Données de démo
make seed-demo
```

Frontend : http://localhost:3000  
Backend API : http://localhost:8000

---

## Variables d'environnement

Copier `.env.example` → `.env` et renseigner :

| Variable | Description | Exemple |
|---|---|---|
| `SECRET_KEY` | Clé secrète Django | `django-insecure-xxx` |
| `DEBUG` | Mode debug | `True` |
| `DB_NAME` | Nom base PostgreSQL | `orbi7rack` |
| `DB_USER` | Utilisateur PostgreSQL | `postgres` |
| `DB_PASSWORD` | Mot de passe PostgreSQL | `postgres` |
| `TRACK17_API_KEY` | Clé API 17TRACK | `xxxxxxxx` |
| `REDIS_URL` | URL Redis | `redis://redis:6379/0` |
| `NEXT_PUBLIC_API_URL` | URL backend pour le frontend | `http://localhost:8000` |

---

## Commandes Makefile

| Commande | Description |
|---|---|
| `make build` | Build les images Docker |
| `make up` | Démarre tous les services |
| `make down` | Arrête tout |
| `make migrate` | Applique les migrations Django |
| `make seed-demo` | Insère 3 colis de démo avec SimulationEngine |
| `make test` | Lance les tests pytest |
| `make shell` | Shell Django interactif |
| `make logs` | Logs du backend en live |

---

## Architecture

```
orbi7rack/
├── backend/
│   ├── apps/
│   │   └── tracking/
│   │       ├── models.py           # Parcel, TrackingEvent (+champs simulés)
│   │       ├── serializers.py      # get_estimated_position (position interpolée)
│   │       ├── parser.py           # Parse 17TRACK → TrackingEvent + géocodage
│   │       ├── tasks.py            # Celery : sync_parcels, compute_simulation
│   │       └── services/
│   │           └── simulation_engine.py  # Haversine, slerp, detect_mode
│   ├── config/                     # Settings, URLs, WSGI
│   ├── scripts/
│   │   └── seed_demo.py            # Données de démo (CN→FR, DE→FR, KR→FR)
│   └── requirements.txt
├── frontend/
│   ├── components/
│   │   ├── GlobeView.tsx           # Globe 3D + arcs + marqueurs
│   │   ├── Sidebar.tsx             # Liste des colis
│   │   └── AddParcelModal.tsx      # Modal d'ajout
│   ├── hooks/
│   │   └── useParcels.ts           # Fetch + polling des colis
│   └── context/
│       ├── AuthContext.tsx         # JWT auth
│       └── ThemeContext.tsx        # Light/dark mode
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Screenshots

<!-- SCREENSHOT : vue globe dark mode — arcs multicolores + sidebar liste des colis -->
<!-- [ insérer captures/globe-dark.png ] -->

<!-- SCREENSHOT : vue globe light mode -->
<!-- [ insérer captures/globe-light.png ] -->

<!-- SCREENSHOT : modal d'ajout de colis -->
<!-- [ insérer captures/add-parcel-modal.png ] -->

<!-- SCREENSHOT : détail colis sélectionné avec timeline d'events -->
<!-- [ insérer captures/parcel-detail.png ] -->

---

## Licence

MIT
