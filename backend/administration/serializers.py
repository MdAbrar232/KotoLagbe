from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

Place = apps.get_model("places", "Place")
User = get_user_model()


class PlaceAdminSerializer(serializers.ModelSerializer):
    """Exposes every field of the Place model, whatever the teammate adds to it."""

    class Meta:
        model = Place
        fields = "__all__"


UserProfile = apps.get_model("accounts", "UserProfile")

_USER_FIELDS = [
    "id", "username", "email", "is_active", "is_staff",
    "is_superuser", "date_joined", "last_login",
]
_existing = {f.name for f in User._meta.get_fields()}


def _profile_of(user):
    """The user's profile, or None if it was never created."""
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


class UserAdminSerializer(serializers.ModelSerializer):
    """Read-only account summary, including the profile information."""

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

    def get_full_name(self, user):
        return self._profile_value(user, "full_name")

    def get_gender(self, user):
        return self._profile_value(user, "gender", "prefer_not_to_say")

    def get_location(self, user):
        return self._profile_value(user, "location")

    def get_bio(self, user):
        return self._profile_value(user, "bio")


class UserAdminUpdateSerializer(serializers.Serializer):
    """What an administrator may change on another user's account."""

    username = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(max_length=120, required=False)
    gender = serializers.ChoiceField(choices=UserProfile.GENDER_CHOICES, required=False)
    location = serializers.CharField(max_length=120, required=False, allow_blank=True)
    bio = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Username cannot be empty.")
        if User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Full name cannot be empty.")
        return value

    @transaction.atomic
    def update(self, user, validated_data):
        for field in ("username", "email"):
            if field in validated_data:
                setattr(user, field, validated_data[field])
        user.save()

        profile_data = {k: v for k, v in validated_data.items()
                        if k in ("full_name", "gender", "location", "bio")}
        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(
                user=user, defaults={"full_name": user.username, "location": ""}
            )
            for key, value in profile_data.items():
                setattr(profile, key, value)
            profile.save()
        return user
