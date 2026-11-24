from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Place(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    area = models.CharField(max_length=150)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    location = models.ForeignKey(
        "transport.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="places",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    average_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "pk"]
        indexes = [
            models.Index(fields=["location"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return self.name


class ItemStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class PlaceItem(models.Model):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="items",
    )

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="item_suggestions",
    )

    status = models.CharField(
        max_length=8,
        choices=ItemStatus.choices,
        default=ItemStatus.PENDING,
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_item_suggestions",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "pk"]
        indexes = [
            models.Index(fields=["place", "status"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.place.name}"


class ItemPriceSubmission(models.Model):
    item = models.ForeignKey(
        PlaceItem,
        on_delete=models.CASCADE,
        related_name="price_submissions",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="item_price_submissions",
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    status = models.CharField(
        max_length=8,
        choices=ItemStatus.choices,
        default=ItemStatus.PENDING,
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_item_prices",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at", "-pk"]
        indexes = [
            models.Index(fields=["item", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gt=0),
                name="places_positive_item_price",
            ),
        ]

    def __str__(self):
        return f"{self.item.name}: {self.price} BDT"


class PlaceReview(models.Model):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="place_reviews",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )

    comment = models.TextField(blank=True)

    status = models.CharField(
        max_length=8,
        choices=ItemStatus.choices,
        default=ItemStatus.PENDING,
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_place_reviews",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["place", "user"],
                name="places_one_review_per_user",
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="places_review_rating_range",
            ),
        ]
        indexes = [
            models.Index(fields=["place", "status"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.place}: {self.rating}/5"