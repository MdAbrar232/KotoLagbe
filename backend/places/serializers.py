from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Q
from rest_framework import serializers

from .models import (
    Place,
    PlaceItem,
    ItemPriceSubmission,
    ItemStatus,
    PlaceReview,
)


class PlaceSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
    )

    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
    )

    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        read_only=True,
        allow_null=True,
        default=None,
    )

    review_count = serializers.IntegerField(
        read_only=True,
        default=0,
    )

    class Meta:
        model = Place
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def validate_parent(self, value):
        if value is None:
            return value

        if self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError(
                "A place cannot be its own parent."
            )

        current = value
        visited = set()

        while current is not None:
            if self.instance and current.pk == self.instance.pk:
                raise serializers.ValidationError(
                    "This relationship would create a circular hierarchy."
                )

            if current.pk in visited:
                raise serializers.ValidationError(
                    "The existing place hierarchy contains a cycle."
                )

            visited.add(current.pk)
            current = current.parent

        return value


class PlaceItemSerializer(serializers.ModelSerializer):
    average_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        allow_null=True,
    )

    place_name = serializers.CharField(
        source="place.name",
        read_only=True,
    )

    class Meta:
        model = PlaceItem
        fields = [
            "id",
            "place",
            "place_name",
            "name",
            "category",
            "description",
            "average_price",
            "created_at",
        ]
        read_only_fields = fields


class SuggestPlaceItemSerializer(serializers.Serializer):
    place = serializers.PrimaryKeyRelatedField(
        queryset=Place.objects.all()
    )

    name = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=80)

    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        write_only=True,
    )

    def validate_name(self, value):
        return value.strip()

    def validate_category(self, value):
        return value.strip()

    def create(self, validated_data):
        request = self.context["request"]

        with transaction.atomic():
            price = validated_data.pop("price")

            item = PlaceItem.objects.create(
                **validated_data,
                submitted_by=request.user,
                status=ItemStatus.PENDING,
            )

            ItemPriceSubmission.objects.create(
                item=item,
                submitted_by=request.user,
                price=price,
                status=ItemStatus.PENDING,
            )

        return item


class ItemPriceSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemPriceSubmission
        fields = [
            "id",
            "item",
            "submitted_by",
            "price",
            "status",
            "submitted_at",
        ]
        read_only_fields = [
            "id",
            "item",
            "submitted_by",
            "status",
            "submitted_at",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than zero."
            )
        return value


class PlaceReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:
        model = PlaceReview
        fields = [
            "id",
            "place",
            "user",
            "username",
            "rating",
            "comment",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "place",
            "user",
            "username",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )
        return value

    def validate_comment(self, value):
        return value.strip()