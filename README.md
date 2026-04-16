# Orbi7rack 🌐

> Parcel tracking reimagined — holographic 3D globe, real-time updates, flight simulation.

## Stack

- **Backend** : Django 5 + Django REST Framework
- **Database** : PostgreSQL 16
- **Queue** : Celery + Redis
- **Frontend** : HTML/CSS/JS + [globe.gl](https://globe.gl) (Three.js)
- **Tracking API** : [17TRACK](https://api.17track.net)
- **Infra** : Docker Compose + Makefile

## Quickstart

```bash
# 1. Clone
git clone https://github.com/windowMaker27/orbi7rack.git
cd orbi7rack

# 2. Configure
cp .env.example .env
# → Remplis les valeurs dans .env

# 3. Build & start
make build
make up
make migrate
```

App dispo sur http://localhost:8000

## Commandes utiles

| Commande | Description |
|---|---|
| `make up` | Démarre tous les services |
| `make down` | Arrête tout |
| `make migrate` | Applique les migrations |
| `make test` | Lance les tests pytest |
| `make shell` | Shell Django interactif |
| `make seed` | Insère des données de démo |
| `make logs` | Logs du backend en live |

## Structure

```
orbi7rack/
├── backend/
│   ├── apps/
│   │   ├── tracking/   # Modèles Parcel, TrackingEvent
│   │   ├── users/      # Auth JWT
│   │   └── api/        # Endpoints REST
│   ├── config/         # Settings, URLs, WSGI
│   └── requirements.txt
├── frontend/           # Globe 3D + UI
├── scripts/            # Utilitaires bash
├── docker-compose.yml
└── Makefile
```

## Licence

MIT
