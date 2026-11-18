from rest_framework import serializers

from .models import FareSubmission, Location, TransportMode


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name", "area", "description", "latitude", "longitude"]
        # Send JSON numbers to the map while retaining decimal input validation.
        extra_kwargs = {
            "latitude": {"coerce_to_string": False},
            "longitude": {"coerce_to_string": False},
        }


class TransportModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportMode
        fields = ["id", "name"]


class FareSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FareSubmission
        fields = [
            "id", "origin", "destination", "transport_mode", "fare",
            "submitted_by", "submitted_at", "status",
        ]
        read_only_fields = ["id", "submitted_by", "submitted_at", "status"]
        extra_kwargs = {"fare": {"coerce_to_string": True}}

    def validate(self, attrs):
        if attrs["origin"] == attrs["destination"]:
            raise serializers.ValidationError({
                "destination": "Choose a destination different from the origin."
            })
        return attrs


class RouteFilterSerializer(serializers.Serializer):
    origin = serializers.IntegerField(min_value=1, required=False)
    destination = serializers.IntegerField(min_value=1, required=False)
    transport_mode = serializers.IntegerField(min_value=1, required=False)
