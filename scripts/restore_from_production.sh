#!/usr/bin/env bash
# restore_from_production.sh - safely restore a production pg_dump + media
# backup onto this host.
#
# This does NOT restore onto the existing database in place. pg_dump --clean
# (used by `make backup`) emits DROP TABLE without CASCADE, which fails
# against a database that already has FK-linked data - the restore then
# silently continues past the failed DROP/CREATE and produces a corrupted,
# partially-populated database (this happened during the initial staging
# migration: only 1 of 73 employee rows survived). The fix is to drop and
# recreate the database first so the dump always lands on an empty schema.
#
# Usage:
#   ./scripts/restore_from_production.sh [horilla_backup.sql] [media_backup.zip]
#   (both arguments optional, default to the filenames `make backup` writes)
#
# Environment overrides: APP_CONTAINER, APP_SERVICE, DB_CONTAINER, PGUSER,
# PGDATABASE, PGPASSWORD, MEDIA_DIR.
set -euo pipefail

APP_CONTAINER=${APP_CONTAINER:-horilla}
APP_SERVICE=${APP_SERVICE:-server}
DB_CONTAINER=${DB_CONTAINER:-postgres}
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-horilla}
PGPASSWORD=${PGPASSWORD:-mysecretpassword}
MEDIA_DIR=${MEDIA_DIR:-media}

DB_DUMP=${1:-horilla_backup.sql}
MEDIA_ZIP=${2:-media_backup.zip}

if [ ! -f "$DB_DUMP" ]; then
    echo "FAIL: database dump not found: ${DB_DUMP}" >&2
    exit 1
fi
if [ ! -f "$MEDIA_ZIP" ]; then
    echo "FAIL: media archive not found: ${MEDIA_ZIP}" >&2
    exit 1
fi

if [ "${CONFIRM_RESTORE:-}" != "yes" ]; then
    echo "This will DESTROY the current '${PGDATABASE}' database and '${MEDIA_DIR}/' contents"
    echo "on this host, replacing them with ${DB_DUMP} and ${MEDIA_ZIP}."
    read -r -p "Type 'yes' to continue: " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        exit 1
    fi
fi

echo "=== Stopping the app ==="
docker compose stop "$APP_SERVICE"

echo "=== Recreating '${PGDATABASE}' clean (terminate connections, drop, create) ==="
docker exec "$DB_CONTAINER" psql -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname = '${PGDATABASE}' AND pid <> pg_backend_pid();
"
docker exec "$DB_CONTAINER" psql -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS ${PGDATABASE};"
docker exec "$DB_CONTAINER" psql -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE ${PGDATABASE} OWNER ${PGUSER};"

if grep -q 'leave_calendar_readonly_user' "$DB_DUMP"; then
    echo "=== Pre-creating leave_calendar_readonly_user (dump grants reference it) ==="
    docker exec "$DB_CONTAINER" psql -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 -c "
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'leave_calendar_readonly_user') THEN
            CREATE USER leave_calendar_readonly_user WITH PASSWORD 'readonlypassword';
        END IF;
    END\$\$;
    "
fi

echo "=== Restoring database from ${DB_DUMP} ==="
docker cp "$DB_DUMP" "$DB_CONTAINER":/tmp/restore_dump.sql
RESTORE_LOG=$(mktemp)
docker exec "$DB_CONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" -f /tmp/restore_dump.sql \
    > "$RESTORE_LOG" 2>&1 || true
docker exec "$DB_CONTAINER" rm -f /tmp/restore_dump.sql

# pg_dump --clean emits harmless DROP ... does-not-exist errors against the
# empty database we just created (no IF EXISTS in the dump). Any OTHER error
# here (duplicate key, FK violation, already-exists) means the restore did
# not land on a truly clean database and must not be treated as successful.
if grep 'ERROR' "$RESTORE_LOG" | grep -v 'does not exist' | grep -q .; then
    echo "FAIL: restore produced unexpected errors (see ${RESTORE_LOG}):" >&2
    grep 'ERROR' "$RESTORE_LOG" | grep -v 'does not exist' >&2
    exit 1
fi
rm -f "$RESTORE_LOG"

echo "=== Restoring media from ${MEDIA_ZIP} ==="
rm -rf "${MEDIA_DIR:?}"/*
unzip -oq "$MEDIA_ZIP" -d .

echo "=== Rebuilding and starting the app ==="
docker compose up -d --build "$APP_SERVICE"

echo
echo "Restore complete. Next steps:"
echo "  1. Check boot logs:      docker logs ${APP_CONTAINER} --tail 40"
echo "  2. Run the audit:        ./scripts/audit_migrations.sh ${DB_DUMP}"
echo "  3. Smoke test the app before pointing DNS here."
