#!/bin/bash
# Deploys the v2 stack in /root/bevy-horilla-v2.
# A push to the git branch named staging still runs this script, and this
# script fast-forwards bevy-hr-portal-dev-2.0. It does not start the v1 app
# or touch the v1 database volume.
set -euo pipefail
cd /root/bevy-horilla-v2

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "Refusing to deploy: tracked files differ from git."
  git status -sb
  exit 1
fi

for file in docker-compose.yml docker-compose.prod.yml docker-compose.staging.yml; do
  if grep -Eq '^[[:space:]]*-[[:space:]]*"?5432:5432"?[[:space:]]*$' "$file"; then
    echo "Refusing to deploy: Postgres would be published on every interface."
    exit 1
  fi
done

git fetch origin bevy-hr-portal-dev-2.0
git checkout bevy-hr-portal-dev-2.0
git pull --ff-only origin bevy-hr-portal-dev-2.0

if [ ! -s .env ] || ! grep -q '^POSTGRES_PASSWORD=.' .env || ! grep -q '^SECRET_KEY=.' .env; then
  echo "Refusing to deploy: /root/bevy-horilla-v2/.env is incomplete."
  exit 1
fi

docker compose -p horilla-v2 \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.staging.yml \
  up --build -d

deadline=$((SECONDS + 720))
while [ "$SECONDS" -lt "$deadline" ]; do
  status="$(docker inspect -f '{{.State.Status}}' horilla-v2-web-1)"
  if [ "$status" != "running" ]; then
    echo "v2 web container is ${status}."
    docker compose -p horilla-v2 logs web --since 10m
    exit 1
  fi
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 -H 'Host: hr-portal.bevy.dev' http://127.0.0.1/login/ || true)"
  health="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 -H 'Host: hr-portal.bevy.dev' http://127.0.0.1/health/ || true)"
  if [ "$code" = "200" ] && [ "$health" = "200" ]; then
    if docker compose -p horilla-v2 logs web --since 10m | grep -q 'Traceback'; then
      echo "v2 boot raised an exception."
      exit 1
    fi
    exit 0
  fi
  sleep 5
done

echo "Staging did not answer on /login/ and /health/ within 12 minutes."
docker compose -p horilla-v2 logs web --since 10m
exit 1
