from rest_framework import generics, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly

from .models import FareStatus, FareSubmission, Location, TransportMode
from .serializers import (
    FareSubmissionSerializer, LocationSerializer,
    RouteFilterSerializer, TransportModeSerializer,
)


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class TransportModeList(generics.ListAPIView):
    queryset = TransportMode.objects.all()
    serializer_class = TransportModeSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class FareListCreate(generics.ListCreateAPIView):
    queryset = FareSubmission.objects.filter(status=FareStatus.APPROVED)
    serializer_class = FareSubmissionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        filters = RouteFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return super().get_queryset().filter(**filters.validated_data)

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user, status=FareStatus.PENDING)
