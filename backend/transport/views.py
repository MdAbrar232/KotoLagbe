from decimal import Decimal

from django.db.models import Avg, Count, Max, Min
from django.shortcuts import get_object_or_404

from rest_framework import generics, viewsets
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from .models import (
    FareStatus,
    FareSubmission,
    Location,
    LocationStatus,
    TransportMode,
)
from .serializers import (
    FareSubmissionSerializer,
    LocationSerializer,
    RouteFareSummaryQuerySerializer,
    RouteFilterSerializer,
    TransportModeSerializer,
)


class LocationViewSet(viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    pagination_class = None
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Location.objects.filter(
            status=LocationStatus.APPROVED
        )

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]

        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(
            submitted_by=self.request.user,
            status=LocationStatus.PENDING,
        )


class TransportModeList(generics.ListAPIView):
    queryset = TransportMode.objects.filter(is_active=True)
    serializer_class = TransportModeSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class FareListCreate(generics.ListCreateAPIView):
    queryset = FareSubmission.objects.filter(
        status=FareStatus.APPROVED,
        transport_mode__is_active=True,
        origin__status=LocationStatus.APPROVED,
        destination__status=LocationStatus.APPROVED,
    )
    serializer_class = FareSubmissionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        filters = RouteFilterSerializer(
            data=self.request.query_params
        )
        filters.is_valid(raise_exception=True)

        return super().get_queryset().filter(
            **filters.validated_data
        )

    def perform_create(self, serializer):
        serializer.save(
            submitted_by=self.request.user,
            status=FareStatus.PENDING,
        )


class RouteFareSummary(generics.GenericAPIView):
    serializer_class = RouteFareSummaryQuerySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get(self, request, *args, **kwargs):
        query_serializer = self.get_serializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        origin_id = query_serializer.validated_data["origin"]
        destination_id = query_serializer.validated_data["destination"]

        origin = get_object_or_404(
            Location,
            pk=origin_id,
            status=LocationStatus.APPROVED,
        )

        destination = get_object_or_404(
            Location,
            pk=destination_id,
            status=LocationStatus.APPROVED,
        )

        fare_summary = (
            FareSubmission.objects.filter(
                origin=origin,
                destination=destination,
                status=FareStatus.APPROVED,
                transport_mode__is_active=True,
            )
            .values(
                "transport_mode_id",
                "transport_mode__name",
            )
            .annotate(
                average_fare=Avg("fare"),
                minimum_fare=Min("fare"),
                maximum_fare=Max("fare"),
                submission_count=Count("pk"),
            )
            .order_by("transport_mode__name")
        )

        transport_options = []

        for row in fare_summary:
            average = row["average_fare"].quantize(
                Decimal("0.01")
            )

            transport_options.append({
                "transport_mode": row["transport_mode__name"],
                "average_fare": f"{average:.2f}",
                "minimum_fare": f'{row["minimum_fare"]:.2f}',
                "maximum_fare": f'{row["maximum_fare"]:.2f}',
                "submission_count": row["submission_count"],
            })

        return Response({
            "origin": {
                "id": origin.pk,
                "name": origin.name,
            },
            "destination": {
                "id": destination.pk,
                "name": destination.name,
            },
            "transport_options": transport_options,
        })