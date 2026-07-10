from django.db import migrations


class Migration(migrations.Migration):
    """
    Reconciling migration for databases whose django_migrations ledger
    recorded horilla_backup.0001_initial before GoogleDriveBackup moved from
    service-account-file auth to OAuth, so the table on disk still has
    service_account_file and lacks the four OAuth columns.

    Database-only and idempotent. Migration state is already correct after
    0001_initial (whose CreateModel defines the OAuth fields), so no state
    operations are needed here:

    - fresh install: 0001_initial creates the table with the OAuth columns,
      every statement here is a no-op
    - drifted ledger (prod): 0001_initial is skipped as already-recorded,
      this drops the orphaned service_account_file column (no remaining
      code references) and adds the missing OAuth columns

    Column types mirror 0001_initial: FileField -> varchar(100),
    TextField -> text, DateTimeField -> timestamptz. Intentionally
    irreversible: reversing a reconciliation of unknown prior state should
    refuse loudly rather than guess.
    """

    dependencies = [
        ("horilla_backup", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE horilla_backup_googledrivebackup
                DROP COLUMN IF EXISTS service_account_file;
            ALTER TABLE horilla_backup_googledrivebackup
                ADD COLUMN IF NOT EXISTS oauth_credentials_file varchar(100) NULL;
            ALTER TABLE horilla_backup_googledrivebackup
                ADD COLUMN IF NOT EXISTS access_token text NULL;
            ALTER TABLE horilla_backup_googledrivebackup
                ADD COLUMN IF NOT EXISTS refresh_token text NULL;
            ALTER TABLE horilla_backup_googledrivebackup
                ADD COLUMN IF NOT EXISTS token_expiry timestamp with time zone NULL;
            """,
        ),
    ]
