#!/usr/bin/env bash
# audit_migrations.sh - verify the committed migrations fully provision a
# database, without touching the live one. Run on the docker-compose host.
#
# Scenario 1 (always):  FRESH database. Every committed migration must apply
#     cleanly to an empty database, `makemigrations --check` must report no
#     drift between models.py and the migration set, and every model column
#     must exist in the resulting schema.
#
# Scenario 2 (optional): TRANSITION audit. Pass a production pg_dump file:
#     it is restored into a scratch database and migrations are applied on
#     top - exactly what happens when this code ships against the real
#     production data. The result must match models.py.
#
# Usage:
#   ./scripts/audit_migrations.sh                      # scenario 1 only
#   ./scripts/audit_migrations.sh horilla_backup.sql   # scenarios 1 + 2
#
# Environment overrides: APP_CONTAINER, DB_CONTAINER, PGUSER, PGPASSWORD.
set -euo pipefail

APP=${APP_CONTAINER:-horilla}
DB=${DB_CONTAINER:-postgres}
PGUSER=${PGUSER:-postgres}
PGPASSWORD=${PGPASSWORD:-mysecretpassword}
AUDIT_DB=migration_audit
DUMP=${1:-}

AUDIT_URL="postgres://${PGUSER}:${PGPASSWORD}@postgres:5432/${AUDIT_DB}"

recreate_db() {
    docker exec "$DB" psql -U "$PGUSER" -d postgres \
        -c "DROP DATABASE IF EXISTS ${AUDIT_DB};" >/dev/null
    docker exec "$DB" psql -U "$PGUSER" -d postgres \
        -c "CREATE DATABASE ${AUDIT_DB};" >/dev/null
}

migrate_all() {
    docker exec -e DATABASE_URL="$AUDIT_URL" "$APP" \
        python3 manage.py migrate --no-input
}

drift_check() {
    # Fails when models.py contains changes not covered by any committed
    # migration - the exact gap that used to be papered over by running
    # makemigrations at container boot.
    docker exec -e DATABASE_URL="$AUDIT_URL" "$APP" \
        python3 manage.py makemigrations --check --dry-run
}

schema_diff() {
    # Compare every concrete model column against the audit database.
    # local_concrete_fields restricts the check to columns each table
    # actually owns (avoids multi-table-inheritance false positives).
    docker exec -e DATABASE_URL="$AUDIT_URL" "$APP" python3 manage.py shell -c "
from django.apps import apps
from django.db import connection

missing_tables, missing_cols = [], []
with connection.cursor() as cur:
    for model in apps.get_models():
        if not model._meta.managed or model._meta.proxy:
            continue
        table = model._meta.db_table
        cur.execute(
            'SELECT column_name FROM information_schema.columns WHERE table_name = %s',
            [table],
        )
        cols = {r[0] for r in cur.fetchall()}
        if not cols:
            missing_tables.append(table)
            continue
        for f in model._meta.local_concrete_fields:
            if f.column and f.column not in cols:
                missing_cols.append(f'{table}.{f.column}')

print('missing tables :', missing_tables or 'none')
print('missing columns:', missing_cols or 'none')
assert not missing_tables and not missing_cols, 'SCHEMA DRIFT DETECTED'
"
}

echo '=== Scenario 1: fresh database ==='
recreate_db
migrate_all
drift_check
schema_diff
echo 'PASS: fresh database provisions cleanly and matches models.py'

if [ -n "$DUMP" ]; then
    echo "=== Scenario 2: restore ${DUMP}, then migrate ==="
    recreate_db
    docker cp "$DUMP" "$DB":/tmp/audit_dump.sql
    docker exec "$DB" psql -U "$PGUSER" -d "$AUDIT_DB" \
        -f /tmp/audit_dump.sql >/tmp/audit_restore.log 2>&1 || true
    # pg_dump --clean emits harmless DROP ... does-not-exist errors on an
    # empty target, and GRANTs to optional roles; anything else is fatal.
    if grep 'ERROR' /tmp/audit_restore.log \
        | grep -v 'does not exist' \
        | grep -q .; then
        echo 'FAIL: restore produced unexpected errors:'
        grep 'ERROR' /tmp/audit_restore.log | grep -v 'does not exist'
        exit 1
    fi
    migrate_all
    schema_diff
    echo 'PASS: restored dump + migrate matches models.py'
fi

docker exec "$DB" psql -U "$PGUSER" -d postgres \
    -c "DROP DATABASE IF EXISTS ${AUDIT_DB};" >/dev/null
echo 'Audit complete.'
