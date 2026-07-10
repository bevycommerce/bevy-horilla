from django.db import migrations


class Migration(migrations.Migration):
    """
    Reconciling migration for databases whose django_migrations ledger
    already recorded attendance.0001_initial/0002_initial (generated
    per-container while migrations were gitignored) without the approved_by
    column ever landing on disk.

    Database-only and idempotent. Migration state is already correct after
    0002_initial (which defines approved_by), so no state operations are
    needed here. The guarded SQL makes every scenario safe:

    - fresh install: 0002_initial creates the columns, this is a no-op
    - drifted ledger (prod): 0001/0002 are skipped as already-recorded,
      this adds the missing columns, FK and index
    - manually hot-fixed database (column added via raw ALTER TABLE):
      this is a no-op

    Postgres-specific (DO block), matching the docker-compose deployment.
    Intentionally irreversible: reversing a reconciliation of unknown prior
    state should refuse loudly rather than guess.
    """

    dependencies = [
        ("employee", "0001_initial"),
        ("attendance", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'attendance_attendance'
                      AND column_name = 'approved_by_id'
                ) THEN
                    ALTER TABLE attendance_attendance
                        ADD COLUMN approved_by_id bigint NULL
                        REFERENCES employee_employee(id)
                        DEFERRABLE INITIALLY DEFERRED;
                    CREATE INDEX attendance_attendance_approved_by_id_reconcile
                        ON attendance_attendance (approved_by_id);
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'attendance_historicalattendance'
                      AND column_name = 'approved_by_id'
                ) THEN
                    ALTER TABLE attendance_historicalattendance
                        ADD COLUMN approved_by_id bigint NULL;
                    CREATE INDEX attendance_historicalatt_approved_by_id_reconcile
                        ON attendance_historicalattendance (approved_by_id);
                END IF;
            END$$;
            """,
        ),
    ]
