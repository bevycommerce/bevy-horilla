import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Reconciling migration: 'approved_by' was present in models.py and in the
    auto-generated 0002_initial migration, but production's database never
    actually received the column (see PR discussion on migrations no longer
    being gitignored). This adds it explicitly under a new migration name so
    it applies regardless of what 0001/0002 are recorded as in an existing
    django_migrations table.
    """

    dependencies = [
        ("employee", "0001_initial"),
        ("attendance", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalattendance",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="employee.employee",
                verbose_name="Approved By",
            ),
        ),
        migrations.AddField(
            model_name="attendance",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="employee.employee",
                verbose_name="Approved By",
            ),
        ),
    ]
