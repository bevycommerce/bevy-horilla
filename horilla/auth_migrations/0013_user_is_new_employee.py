from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration for the is_new_employee field that base/models.py adds to
    django.contrib.auth.User via User.add_to_class().

    While migrations were generated at container boot, makemigrations wrote
    this file into site-packages inside each container (recorded in
    production's ledger as auth.0013_user_is_new_employee - this file must
    keep that exact name). It never existed in any image built from the
    repo, so fresh installs were missing the column and every User query
    crashed. horilla/auth_migrations now owns the auth migration set via
    settings.MIGRATION_MODULES: 0001-0012 are Django 4.2's stock files,
    this adds the patched field.

    SeparateDatabaseAndState so the database step is idempotent: fresh
    installs and drifted-ledger databases both end up correct, and a
    database that already gained the column via a manual hotfix is a no-op.
    """

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="user",
                    name="is_new_employee",
                    field=models.BooleanField(default=False),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE auth_user ADD COLUMN IF NOT EXISTS "
                        "is_new_employee boolean NOT NULL DEFAULT false;"
                    ),
                ),
            ],
        ),
    ]
