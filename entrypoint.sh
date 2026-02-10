#!/bin/bash

echo "Waiting for database to be ready..."
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --noinput
python3 manage.py createhorillauser --first_name bevy --last_name admin --username bevyadmin --password bevyadmin --email hr@bevycommerce.com --phone 1234567890
gunicorn --workers 1 --bind 0.0.0.0:8000 horilla.wsgi:application
