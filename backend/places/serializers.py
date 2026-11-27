
from decimal import Decimal

from django.core import signing
from django.db import transaction
from django.db.models import Avg, Q
from django.urls import reverse
from urllib.parse import urlencode
from rest_framework import serializers

from .models import (
    Place,
    PlaceItem,
    ItemPriceSubmission,
    ItemStatus,
    PlaceReview,
    PlacePhoto,
    Favorite,
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
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        location = instance.location

        if location is None or location.status != "approved":
            representation["location"] = None
            representation["location_name"] = None

        return representation



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
    id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
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
            "image",
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


PLACE_PHOTO_URL_SALT = "kotolagbe.place-photo-preview"


def place_photo_image_url(photo, request=None):
    path = reverse("place-photo-image", args=[photo.pk])

    if photo.status != ItemStatus.APPROVED:
        user = getattr(request, "user", None)
        can_preview = bool(
            user
            and user.is_authenticated
            and (
                user.is_staff
                or photo.submitted_by_id == user.pk
            )
        )
        if not can_preview:
            return None

        token = signing.dumps(
            {"photo_id": photo.pk, "user_id": user.pk},
            salt=PLACE_PHOTO_URL_SALT,
        )
        path = f"{path}?{urlencode({'token': token})}"

    return request.build_absolute_uri(path) if request else path


class PlacePhotoSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    image_upload = serializers.FileField(write_only=True, source="image")
    place_name = serializers.CharField(source="place.name", read_only=True)
    username = serializers.SerializerMethodField()

    class Meta:
        model = PlacePhoto
        fields = [
            "id",
            "place",
            "place_name",
            "submitted_by",
            "username",
            "image",
            "image_upload",
            "caption",
            "status",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "place",
            "place_name",
            "submitted_by",
            "username",
            "status",
            "rejection_reason",
            "created_at",
        ]

    def get_username(self, obj):
        return obj.submitted_by.username if obj.submitted_by else "Deleted user"

    def get_image(self, obj):
        return place_photo_image_url(obj, self.context.get("request"))

    def validate_caption(self, value):
        return value.strip()

    def validate_image_upload(self, value):
        from PIL import Image, UnidentifiedImageError

        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Image must be 5 MB or smaller.")

        try:
            value.seek(0)
            image = Image.open(value)
            image_format = image.format
            width, height = image.size
            if width * height > 25_000_000:
                raise serializers.ValidationError("Image dimensions must not exceed 25 megapixels.")
            image.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise serializers.ValidationError("Upload a valid JPEG, PNG, or WebP image.")
        finally:
            value.seek(0)

        if image_format not in {"JPEG", "PNG", "WEBP"}:
            raise serializers.ValidationError("Only JPEG, PNG, and WebP images are allowed.")

        extension = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        allowed_extensions = {
            "JPEG": {"jpg", "jpeg"},
            "PNG": {"png"},
            "WEBP": {"webp"},
        }
        if extension not in allowed_extensions[image_format]:
            raise serializers.ValidationError("The file extension must match the image format.")

        return value


class FavoriteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["id", "place", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_place(self, value):
        user = self.context["request"].user

        if Favorite.objects.filter(
            user=user,
            place=value,
        ).exists():
            raise serializers.ValidationError(
                "This place is already in your favorites."
            )

        return value

    def create(self, validated_data):
        return Favorite.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )
