#!/bin/bash
# Fail fast: a failed migrate must abort the boot instead of letting
# gunicorn serve traffic against a half-migrated schema.
set -e

echo "Waiting for database to be ready..."
python3 manage.py migrate
python3 manage.py createcachetable
python3 manage.py collectstatic --noinput
# Creates the bootstrap admin only when HORILLA_ADMIN_PASSWORD is set.
# Existing users are left unchanged.
if [ -n "${HORILLA_ADMIN_PASSWORD:-}" ]; then
  python3 manage.py createhorillauser \
    --first_name "${HORILLA_ADMIN_FIRST_NAME:-bevy}" \
    --last_name "${HORILLA_ADMIN_LAST_NAME:-admin}" \
    --username "${HORILLA_ADMIN_USERNAME:-bevyadmin}" \
    --password "$HORILLA_ADMIN_PASSWORD" \
    --email "${HORILLA_ADMIN_EMAIL:-hr@bevycommerce.com}" \
    --phone "${HORILLA_ADMIN_PHONE:-1234567890}" || true
fi
gunicorn --workers 4 --bind 0.0.0.0:8000 horilla.wsgi:application
