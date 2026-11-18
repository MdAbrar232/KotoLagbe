from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class LocationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Location(models.Model):
    name = models.CharField(max_length=200)
    area = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="location_submissions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=8, choices=LocationStatus.choices,
        default=LocationStatus.PENDING, db_index=True,
    )
    latitude = models.DecimalField(
        max_digits=8, decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(latitude__range=(-90, 90)), name="transport_latitude_range"),
            models.CheckConstraint(condition=models.Q(longitude__range=(-180, 180)), name="transport_longitude_range"),
        ]

    def __str__(self):
        return f"{self.name} ({self.area})"


class TransportMode(models.Model):
    name = models.CharField(max_length=80, unique=True)
    # Added for administrative availability control. Existing modes stay active.
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FareStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class FareSubmission(models.Model):
    origin = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="outgoing_fares")
    destination = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="incoming_fares")
    transport_mode = models.ForeignKey(TransportMode, on_delete=models.PROTECT, related_name="fares")
    fare = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Fare paid in Bangladeshi taka (BDT).",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="fare_submissions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=8, choices=FareStatus.choices, default=FareStatus.PENDING, db_index=True)

    class Meta:
        ordering = ["-submitted_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=~models.Q(origin=models.F("destination")), name="transport_distinct_stops",
                                    violation_error_message="Choose a destination different from the origin."),
            models.CheckConstraint(condition=models.Q(fare__gt=0), name="transport_positive_fare"),
            models.CheckConstraint(condition=models.Q(status__in=FareStatus.values), name="transport_valid_fare_status"),
        ]

    def __str__(self):
        return f"{self.origin} to {self.destination} ({self.fare} BDT)"
