from django.utils import timezone

from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from places.models import PlaceReview, ItemStatus
from .models import AdminActivityLog
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


class PlaceReviewModerationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdmin]
    serializer_class = PlaceReviewModerationSerializer

    queryset = PlaceReview.objects.select_related(
        "place",
        "user",
        "reviewed_by",
    ).all()

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "place__name",
        "user__username",
        "comment",
    ]
    ordering_fields = ["created_at", "rating", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        wanted = self.request.query_params.get("status")

        if wanted in ItemStatus.values:
            queryset = queryset.filter(status=wanted)

        return queryset

    def _set_status(self, request, value):
        review = self.get_object()

        if review.user_id == request.user.pk:
            return Response(
                {"detail": "You cannot moderate your own review."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reason = str(request.data.get("reason") or "").strip()

        if value == ItemStatus.REJECTED and not reason:
            return Response(
                {"reason": "A rejection reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        review.status = value
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.rejection_reason = (
            reason if value == ItemStatus.REJECTED else ""
        )

        review.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
        ])

        AdminActivityLog.objects.create(
            actor=request.user,
            action=value,
            entity="place review",
            entity_id=str(review.pk),
            summary=(
                f"{value.title()} review #{review.pk} "
                f"for {review.place.name}"
            ),
        )

        return Response(self.get_serializer(review).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(request, ItemStatus.APPROVED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._set_status(request, ItemStatus.REJECTED)