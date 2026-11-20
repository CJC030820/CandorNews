#!/usr/bin/env bash
# Update the live CandorNews site from GitHub and tidy up afterwards.
#   bash deploy/update.sh                 # rebuild backend and frontend
#   bash deploy/update.sh frontend        # rebuild only the website
#
# Building images is the heaviest job on this 1 GB server; the build cache and
# old images it leaves behind fill the disk and push memory into swap, so they
# are cleared after every update (cache from the last 3 days is kept so the
# next build stays quick).
set -euo pipefail
cd "$(dirname "$0")/.."

SERVICES="${*:-backend frontend}"
COMPOSE="docker compose --env-file deploy/production.env -f docker-compose.prod.yml"

git pull --ff-only
echo "Code: $(git log --oneline -1)"

# shellcheck disable=SC2086
$COMPOSE up -d --build --no-deps $SERVICES

docker builder prune -f --filter until=72h >/dev/null
docker image prune -f >/dev/null
echo "Cleaned old build cache and unused images:"
docker system df | sed -n '1,5p'

echo "Waiting for the updated containers to report healthy..."
for i in $(seq 1 60); do
  unhealthy=$($COMPOSE ps --format '{{.Service}} {{.Status}}' | grep -E "$(echo $SERVICES | tr ' ' '|')" | grep -vc '(healthy)' || true)
  [ "$unhealthy" = "0" ] && break
  sleep 3
done
$COMPOSE ps --format '{{.Service}}: {{.Status}}'
