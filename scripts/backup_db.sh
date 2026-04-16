#!/usr/bin/env bash
# Backup PostgreSQL vers un fichier SQL daté
set -e

FILENAME="backup_$(date +%Y%m%d_%H%M%S).sql"
echo "💾 Backup → $FILENAME"
docker compose exec db pg_dump -U "${DB_USER:-orbi7rack_user}" "${DB_NAME:-orbi7rack}" > "$FILENAME"
echo "✅ Backup sauvegardé : $FILENAME"
