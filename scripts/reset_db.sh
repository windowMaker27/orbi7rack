#!/usr/bin/env bash
# Reset complet de la base de données
set -e

read -p "⚠️  Reset complet de la DB ? (oui/non) : " confirm
[[ "$confirm" != "oui" ]] && echo "Annulé." && exit 0

echo "🗑️  Suppression des volumes..."
docker compose down -v

echo "🚀 Redémarrage..."
docker compose up -d
sleep 5

echo "📦 Migrations..."
docker compose exec backend python manage.py migrate

echo "✅ Base réinitialisée."
