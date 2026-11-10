from django.apps import apps
from django.contrib.auth import get_user_model
from rest_framework import serializers

Place = apps.get_model("places", "Place")
User = get_user_model()


class PlaceAdminSerializer(serializers.ModelSerializer):
    """Exposes every field of the Place model, whatever the teammate adds to it."""

    class Meta:
        model = Place
        fields = "__all__"


_USER_FIELDS = [
    "id", "username", "email", "is_active", "is_staff",
    "is_superuser", "date_joined", "last_login",
]
_existing = {f.name for f in User._meta.get_fields()}


class UserAdminSerializer(serializers.ModelSerializer):
    """Read-only account summary; blocking is done through the block/unblock actions."""

    class Meta:
        model = User
        fields = [f for f in _USER_FIELDS if f in _existing]
        read_only_fields = fields
