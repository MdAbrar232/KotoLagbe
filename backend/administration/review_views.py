from django.db import transaction
from django.utils import timezone

from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from places.models import PlacePhoto, PlaceReview, ItemStatus
from places.photos import PlacePhotoSerializer
from .models import record_activity
from .permissions import IsAdmin


class PlaceReviewModerationSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(
        source="place.name",
        read_only=True,
    )
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )
    reviewer = serializers.SerializerMethodField()

    class Meta:
        model = PlaceReview
        fields = [
            "id",
            "place",
            "place_name",
            "user",
            "username",
            "rating",
            "comment",
            "status",
            "reviewed_by",
            "reviewer",
            "reviewed_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_reviewer(self, obj):
        return obj.reviewed_by.username if obj.reviewed_by else None


class PlaceContributionModerationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    ordering = ["-created_at", "-pk"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ("approve", "reject"):
            queryset = queryset.select_for_update(of=("self",))
        wanted = self.request.query_params.get("status")

        if wanted in ItemStatus.values:
            queryset = queryset.filter(status=wanted)

        return queryset

    @transaction.atomic
    def _set_status(self, request, value):
        contribution = self.get_object()

        if contribution.user_id == request.user.pk:
            return Response(
                {"detail": f"You cannot moderate your own {self.kind}."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reason = str(request.data.get("reason") or "").strip()

        if value == ItemStatus.REJECTED and not reason:
            return Response(
                {"reason": "A rejection reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contribution.status = value
        contribution.reviewed_by = request.user
        contribution.reviewed_at = timezone.now()
        contribution.rejection_reason = reason if value == ItemStatus.REJECTED else ""

        contribution.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
        ])

        record_activity(request, value, f"place {self.kind}", contribution,
                        f"{value.title()} {self.kind} #{contribution.pk} for {contribution.place.name}")
        return Response(self.get_serializer(contribution).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(request, ItemStatus.APPROVED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._set_status(request, ItemStatus.REJECTED)


class PlaceReviewModerationViewSet(PlaceContributionModerationViewSet):
    kind = "review"
    queryset = PlaceReview.objects.select_related("place", "user", "reviewed_by")
    serializer_class = PlaceReviewModerationSerializer
    search_fields = ["place__name", "user__username", "comment"]
    ordering_fields = ["created_at", "rating", "status"]


class PlacePhotoModerationViewSet(PlaceContributionModerationViewSet):
    kind = "photo"
    queryset = PlacePhoto.objects.select_related("place", "user", "reviewed_by")
    serializer_class = PlacePhotoSerializer
    search_fields = ["place__name", "user__username", "caption"]
    ordering_fields = ["created_at", "status"]
