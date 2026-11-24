from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from places.models import PlaceItem, ItemPriceSubmission
from transport.models import Location, FareSubmission

from .models import UserProfile, StatusPost


class RegisterSerializer(serializers.Serializer):

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    full_name = serializers.CharField(max_length=120)

    gender = serializers.ChoiceField(
        choices=UserProfile.GENDER_CHOICES,
        required=False,
        default="prefer_not_to_say"
    )

    location = serializers.CharField(max_length=120)

    bio = serializers.CharField(
        max_length=300,
        required=False,
        allow_blank=True,
        default=""
    )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "This username is already taken."
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email is already registered."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):

        profile_data = {
            "full_name": validated_data.pop("full_name"),
            "gender": validated_data.pop("gender"),
            "location": validated_data.pop("location"),
            "bio": validated_data.pop("bio"),
        }

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"]
        )

        UserProfile.objects.create(
            user=user,
            **profile_data
        )

        return user


class LoginSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):

        data = super().validate(attrs)

        profile, created = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                "full_name": self.user.username,
                "location": "",
            }
        )

        data["username"] = self.user.username
        data["email"] = self.user.email
        data["is_staff"] = self.user.is_staff

        data["full_name"] = profile.full_name
        data["gender"] = profile.gender
        data["location"] = profile.location
        data["bio"] = profile.bio

        return data


class UserProfileSerializer(serializers.ModelSerializer):

    username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    class Meta:
        model = UserProfile

        fields = [
            "username",
            "email",
            "full_name",
            "gender",
            "location",
            "bio",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "username",
            "email",
            "created_at",
            "updated_at",
        ]


class StatusPostSerializer(serializers.ModelSerializer):

    author_username = serializers.CharField(
        source="author.username",
        read_only=True
    )

    author_full_name = serializers.SerializerMethodField()
    author_location = serializers.SerializerMethodField()

    class Meta:
        model = StatusPost

        fields = [
            "id",
            "content",
            "author_username",
            "author_full_name",
            "author_location",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "author_username",
            "author_full_name",
            "author_location",
            "created_at",
        ]

    def get_author_full_name(self, obj):
        try:
            return obj.author.profile.full_name
        except UserProfile.DoesNotExist:
            return obj.author.username

    def get_author_location(self, obj):
        try:
            return obj.author.profile.location
        except UserProfile.DoesNotExist:
            return ""

    def validate_content(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Post content cannot be empty."
            )

        return value


# --------------------------------------------------
# Submission history serializers
# --------------------------------------------------

class LocationSubmissionSerializer(serializers.ModelSerializer):

    type = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            "type",
            "id",
            "name",
            "area",
            "status",
            "submitted_at",
        ]

    def get_type(self, obj):
        return "location"


class FareSubmissionHistorySerializer(serializers.ModelSerializer):

    type = serializers.SerializerMethodField()
    origin_name = serializers.CharField(
        source="origin.name",
        read_only=True
    )
    destination_name = serializers.CharField(
        source="destination.name",
        read_only=True
    )
    transport_mode_name = serializers.CharField(
        source="transport_mode.name",
        read_only=True
    )

    class Meta:
        model = FareSubmission
        fields = [
            "type",
            "id",
            "origin",
            "origin_name",
            "destination",
            "destination_name",
            "transport_mode",
            "transport_mode_name",
            "fare",
            "status",
            "submitted_at",
        ]

    def get_type(self, obj):
        return "fare"


class PlaceItemSubmissionSerializer(serializers.ModelSerializer):

    type = serializers.SerializerMethodField()
    place_name = serializers.CharField(
        source="place.name",
        read_only=True
    )
    submitted_at = serializers.DateTimeField(
        source="created_at",
        read_only=True
    )

    class Meta:
        model = PlaceItem
        fields = [
            "type",
            "id",
            "name",
            "category",
            "place",
            "place_name",
            "status",
            "rejection_reason",
            "submitted_at",
        ]

    def get_type(self, obj):
        return "place_item"


class ItemPriceSubmissionHistorySerializer(serializers.ModelSerializer):

    type = serializers.SerializerMethodField()
    item_name = serializers.CharField(
        source="item.name",
        read_only=True
    )
    place_name = serializers.CharField(
        source="item.place.name",
        read_only=True
    )

    class Meta:
        model = ItemPriceSubmission
        fields = [
            "type",
            "id",
            "item",
            "item_name",
            "place_name",
            "price",
            "status",
            "rejection_reason",
            "submitted_at",
        ]

    def get_type(self, obj):
        return "item_price"