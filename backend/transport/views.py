
from rest_framework import generics, viewsets
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)

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
