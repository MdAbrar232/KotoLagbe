from rest_framework import serializers

from .models import (
    FareSubmission,
    Location,
    LocationStatus,
    TransportMode,
)


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "area",
            "description",
            "latitude",
            "longitude",
        ]
        extra_kwargs = {
            "latitude": {"coerce_to_string": False},
            "longitude": {"coerce_to_string": False},
        }


class TransportModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportMode
        fields = ["id", "name"]


class FareSubmissionSerializer(serializers.ModelSerializer):
    origin = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(status=LocationStatus.APPROVED)
    )
    destination = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(status=LocationStatus.APPROVED)
    )

    class Meta:
        model = FareSubmission
        fields = [
            "id",
            "origin",
            "destination",
            "transport_mode",
            "fare",
            "submitted_by",
            "submitted_at",
            "status",
        ]
        read_only_fields = [
            "id",
            "submitted_by",
            "submitted_at",
            "status",
        ]
        extra_kwargs = {
            "fare": {"coerce_to_string": True},
        }

    def validate_transport_mode(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "This transport mode is currently unavailable."
            )
        return value

    def validate(self, attrs):
        if attrs["origin"] == attrs["destination"]:
            raise serializers.ValidationError({
                "destination": (
                    "Choose a destination different from the origin."
                )
            })
        return attrs


class RouteFilterSerializer(serializers.Serializer):
    origin = serializers.IntegerField(min_value=1, required=False)
    destination = serializers.IntegerField(min_value=1, required=False)
    transport_mode = serializers.IntegerField(min_value=1, required=False)


class RouteFareSummaryQuerySerializer(serializers.Serializer):
    origin = serializers.IntegerField(min_value=1)
    destination = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs["origin"] == attrs["destination"]:
            raise serializers.ValidationError({
                "destination": "Origin and destination must be different."
            })

        return attrs