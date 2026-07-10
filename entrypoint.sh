#!/bin/bash
# Fail fast: a failed migrate must abort the boot instead of letting
# gunicorn serve traffic against a half-migrated schema.
set -e

echo "Waiting for database to be ready..."
python3 manage.py migrate
python3 manage.py createcachetable
python3 manage.py collectstatic --noinput
# Non-fatal: exits with an error when the user already exists, which is the
# normal case on every boot after the first.
python3 manage.py createhorillauser --first_name bevy --last_name admin --username bevyadmin --password bevyadmin --email hr@bevycommerce.com --phone 1234567890 || true
gunicorn --workers 4 --bind 0.0.0.0:8000 horilla.wsgi:application
