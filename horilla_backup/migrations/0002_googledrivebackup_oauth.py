from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Reconciling migration: GoogleDriveBackup moved from service-account-file
    auth to OAuth (see PR discussion on migrations no longer being
    gitignored). Production's database still had the old
    'service_account_file' column and was missing the new OAuth columns
    because 0001_initial was already recorded as applied without them ever
    landing on disk.
    """

    dependencies = [
        ("horilla_backup", "0001_initial"),
    ]

    operations = [
        # service_account_file is already absent from Django's migration
        # state (0001_initial reflects current, OAuth-only models.py) but
        # still lingered as a real column on production's table. Drop it
        # with raw SQL since there is no tracked field for RemoveField.
        migrations.RunSQL(
            sql="ALTER TABLE horilla_backup_googledrivebackup DROP COLUMN IF EXISTS service_account_file;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AddField(
            model_name="googledrivebackup",
            name="oauth_credentials_file",
            field=models.FileField(
                blank=True,
                help_text="Make sure your file is in JSON format and contains your Google OAuth 2.0 client credentials (web application type)",
                null=True,
                upload_to="gdrive_oauth_credentials_file",
                verbose_name="OAuth Credentials File",
            ),
        ),
        migrations.AddField(
            model_name="googledrivebackup",
            name="access_token",
            field=models.TextField(
                blank=True,
                help_text="OAuth access token (automatically managed)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="googledrivebackup",
            name="refresh_token",
            field=models.TextField(
                blank=True,
                help_text="OAuth refresh token (automatically managed)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="googledrivebackup",
            name="token_expiry",
            field=models.DateTimeField(
                blank=True,
                help_text="Token expiry time (automatically managed)",
                null=True,
            ),
        ),
    ]
