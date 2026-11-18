from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


def seed_modes(apps, schema_editor):
    modes = apps.get_model("transport", "TransportMode").objects.using(schema_editor.connection.alias)
    for name in ("Rickshaw", "CNG", "Bus", "Leguna"):
        modes.get_or_create(name=name)


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Location",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("area", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("latitude", models.DecimalField(
                    max_digits=8, decimal_places=6,
                    validators=[MinValueValidator(-90), MaxValueValidator(90)],
                )),
                ("longitude", models.DecimalField(
                    max_digits=9, decimal_places=6,
                    validators=[MinValueValidator(-180), MaxValueValidator(180)],
                )),
            ],
            options={
                "ordering": ["name", "pk"],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(latitude__range=(-90, 90)), name="transport_latitude_range"),
                    models.CheckConstraint(condition=models.Q(longitude__range=(-180, 180)), name="transport_longitude_range"),
                ],
            },
        ),
        migrations.CreateModel(
            name="TransportMode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="FareSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origin", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="outgoing_fares", to="transport.location",
                )),
                ("destination", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="incoming_fares", to="transport.location",
                )),
                ("transport_mode", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="fares", to="transport.transportmode",
                )),
                ("fare", models.DecimalField(
                    max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
                    help_text="Fare paid in Bangladeshi taka (BDT).",
                )),
                ("submitted_by", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fare_submissions",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(
                    max_length=8, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                    db_index=True, default="pending",
                )),
            ],
            options={
                "ordering": ["-submitted_at", "-pk"],
                "constraints": [
                    models.CheckConstraint(
                        condition=~models.Q(origin=models.F("destination")), name="transport_distinct_stops",
                        violation_error_message="Choose a destination different from the origin.",
                    ),
                    models.CheckConstraint(condition=models.Q(fare__gt=0), name="transport_positive_fare"),
                    models.CheckConstraint(
                        condition=models.Q(status__in=["pending", "approved", "rejected"]),
                        name="transport_valid_fare_status",
                    ),
                ],
            },
        ),
        migrations.RunPython(seed_modes, reverse_code=migrations.RunPython.noop),
    ]
