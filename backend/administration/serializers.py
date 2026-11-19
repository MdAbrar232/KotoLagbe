from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from transport.models import FareSubmission, Location, TransportMode
from .models import AdminActivityLog

Place = apps.get_model("places", "Place")
User = get_user_model()


class PlaceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = "__all__"


class LocationAdminSerializer(serializers.ModelSerializer):
    contributor = serializers.CharField(source="submitted_by.username", read_only=True, default=None)

    class Meta:
        model = Location
        fields = ["id", "name", "area", "description", "latitude", "longitude",
                  "status", "submitted_by", "contributor", "submitted_at"]
        read_only_fields = ["id", "submitted_by", "contributor", "submitted_at", "status"]
        extra_kwargs = {"latitude": {"coerce_to_string": False}, "longitude": {"coerce_to_string": False}}


class TransportModeAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportMode
        fields = ["id", "name", "is_active"]

    def validate_name(self, value):
        """Names are unique ignoring capital letters, so "bus" cannot sit next to "Bus"."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be empty.")
        clash = TransportMode.objects.filter(name__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A transport mode with this name already exists.")
        return value


class FareAdminSerializer(serializers.ModelSerializer):
    origin_name = serializers.CharField(source="origin.name", read_only=True)
    origin_area = serializers.CharField(source="origin.area", read_only=True)
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    destination_area = serializers.CharField(source="destination.area", read_only=True)
    transport_mode_name = serializers.CharField(source="transport_mode.name", read_only=True)
    contributor = serializers.SerializerMethodField()

    class Meta:
        model = FareSubmission
        fields = ["id", "origin", "origin_name", "origin_area", "destination", "destination_name", "destination_area",
                  "transport_mode", "transport_mode_name", "fare", "submitted_by", "contributor", "submitted_at", "status"]
        read_only_fields = fields

    def get_contributor(self, obj):
        return obj.submitted_by.username if obj.submitted_by else "Deleted user"


class AdminActivityLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.SerializerMethodField()

    def get_actor_username(self, obj):
        return obj.actor.username if obj.actor else "Deleted admin"

    class Meta:
        model = AdminActivityLog
        fields = ["id", "actor_username", "action", "entity", "entity_id", "summary", "created_at"]
        read_only_fields = fields


UserProfile = apps.get_model("accounts", "UserProfile")
_USER_FIELDS = ["id", "username", "email", "is_active", "is_staff", "is_superuser", "date_joined", "last_login"]
_existing = {f.name for f in User._meta.get_fields()}


def _profile_of(user):
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


class UserAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [f for f in _USER_FIELDS if f in _existing] + ["full_name", "gender", "location", "bio"]
        read_only_fields = fields

    def _profile_value(self, user, name, empty=""):
        profile = _profile_of(user)
        return getattr(profile, name) if profile else empty

    def get_full_name(self, user): return self._profile_value(user, "full_name")
    def get_gender(self, user): return self._profile_value(user, "gender", "prefer_not_to_say")
    def get_location(self, user): return self._profile_value(user, "location")
    def get_bio(self, user): return self._profile_value(user, "bio")


class UserAdminUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(max_length=120, required=False)
    gender = serializers.ChoiceField(choices=UserProfile.GENDER_CHOICES, required=False)
    location = serializers.CharField(max_length=120, required=False, allow_blank=True)
    bio = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate_username(self, value):
        value = value.strip()
        if not value: raise serializers.ValidationError("Username cannot be empty.")
        if User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_full_name(self, value):
        value = value.strip()
        if not value: raise serializers.ValidationError("Full name cannot be empty.")
        return value

    @transaction.atomic
    def update(self, user, validated_data):
        for field in ("username", "email"):
            if field in validated_data: setattr(user, field, validated_data[field])
        user.save()
        profile_data = {k: v for k, v in validated_data.items() if k in ("full_name", "gender", "location", "bio")}
        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"full_name": user.username, "location": ""})
            for key, value in profile_data.items(): setattr(profile, key, value)
            profile.save()
        return user
