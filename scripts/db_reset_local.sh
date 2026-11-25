#!/usr/bin/env bash
# 重建本機資料庫：只動 docker compose 的本機 Postgres，不碰任何正式環境。
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d db
for i in $(seq 1 40); do docker compose exec -T db pg_isready -U leverage -d leverage >/dev/null 2>&1 && break; sleep 1; done
docker compose exec -T db psql -q -U leverage -d leverage -c "drop schema if exists public cascade; create schema public; drop schema if exists app cascade; drop schema if exists auth cascade;" >/dev/null
for f in supabase/local/00_auth_stub.sql supabase/migrations/*.sql; do
  echo "套用 $f"
  docker compose exec -T db psql -v ON_ERROR_STOP=1 -q -U leverage -d leverage < "$f"
done
echo "完成"
