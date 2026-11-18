from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from transport.models import FareStatus, FareSubmission, Location, LocationStatus, TransportMode
from .models import AdminActivityLog
from .permissions import IsAdmin
from .serializers import (
    AdminActivityLogSerializer, FareAdminSerializer, LocationAdminSerializer,
    PlaceAdminSerializer, TransportModeAdminSerializer, UserAdminSerializer,
    UserAdminUpdateSerializer,
)

Place = apps.get_model("places", "Place")
User = get_user_model()
PLACE_FIELDS = {f.name for f in Place._meta.get_fields()}
USER_FIELDS = {f.name for f in User._meta.get_fields()}
HAS_STATUS = "status" in PLACE_FIELDS
PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"


def record_activity(request, action_name, entity, obj, summary):
    AdminActivityLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action_name,
        entity=entity,
        entity_id=str(getattr(obj, "pk", "")),
        summary=summary[:255],
    )


class AuditedModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet that records successful admin changes."""
    permission_classes = [IsAdmin]
    entity_label = "record"

    def perform_create(self, serializer):
        obj = serializer.save()
        record_activity(self.request, "created", self.entity_label, obj, f"Created {self.entity_label}: {obj}")

    def perform_update(self, serializer):
        obj = serializer.save()
        record_activity(self.request, "updated", self.entity_label, obj, f"Updated {self.entity_label}: {obj}")

    def perform_destroy(self, instance):
        label, pk, title = self.entity_label, instance.pk, str(instance)
        instance.delete()
        record_activity(self.request, "deleted", label, type("Deleted", (), {"pk": pk})(), f"Deleted {label}: {title}")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"detail": "This record is referenced by existing fare submissions. Deactivate it or update those records first."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlaceAdminViewSet(AuditedModelViewSet):
    serializer_class = PlaceAdminSerializer
    entity_label = "place"
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [f for f in ("name", "area", "address", "category") if f in PLACE_FIELDS]
    ordering = ("-pk",)

    def get_queryset(self):
        queryset = Place.objects.all()
        wanted = self.request.query_params.get("status")
        if wanted and HAS_STATUS:
            queryset = queryset.filter(status=wanted)
        return queryset

    def _set_status(self, value):
        if not HAS_STATUS:
            return Response({"detail": "Place has no status field, so approval is not enabled."}, status=400)
        place = self.get_object()
        place.status = value
        place.save(update_fields=["status"])
        record_activity(self.request, value, "place", place, f"{value.title()} place: {place}")
        return Response(self.get_serializer(place).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(APPROVED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._set_status(REJECTED)


class LocationAdminViewSet(AuditedModelViewSet):
    queryset = Location.objects.select_related("submitted_by").all()
    serializer_class = LocationAdminSerializer
    entity_label = "location"
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "area", "description", "submitted_by__username"]
    ordering_fields = ["name", "area", "id", "submitted_at", "status"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        wanted = self.request.query_params.get("status")
        if wanted in LocationStatus.values:
            queryset = queryset.filter(status=wanted)
        return queryset

    def perform_create(self, serializer):
        location = serializer.save(status=LocationStatus.APPROVED)
        record_activity(self.request, "created", "location", location, f"Created approved location: {location}")

    def _set_status(self, request, value):
        location = self.get_object()
        location.status = value
        location.save(update_fields=["status"])
        record_activity(request, value, "location", location, f"{value.title()} location: {location}")
        return Response(self.get_serializer(location).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(request, LocationStatus.APPROVED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._set_status(request, LocationStatus.REJECTED)


class TransportModeAdminViewSet(AuditedModelViewSet):
    queryset = TransportMode.objects.all()
    serializer_class = TransportModeAdminSerializer
    entity_label = "transport mode"
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "is_active"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        active = self.request.query_params.get("active")
        if active in ("true", "false"):
            queryset = queryset.filter(is_active=(active == "true"))
        return queryset

    def _set_active(self, request, active):
        mode = self.get_object()
        mode.is_active = active
        mode.save(update_fields=["is_active"])
        action_name = "activated" if active else "deactivated"
        record_activity(request, action_name, "transport mode", mode, f"{action_name.title()} transport mode: {mode.name}")
        return Response(self.get_serializer(mode).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._set_active(request, True)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        return self._set_active(request, False)


class FareAdminViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdmin]
    queryset = FareSubmission.objects.select_related("origin", "destination", "transport_mode", "submitted_by").all()
    serializer_class = FareAdminSerializer
    entity_label = "fare submission"
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["origin__name", "origin__area", "destination__name", "destination__area", "transport_mode__name", "submitted_by__username"]
    ordering_fields = ["submitted_at", "fare", "status"]
    ordering = ["-submitted_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        wanted = self.request.query_params.get("status")
        if wanted in FareStatus.values:
            queryset = queryset.filter(status=wanted)
        return queryset

    def _set_status(self, request, value):
        fare = self.get_object()
        fare.status = value
        fare.save(update_fields=["status"])
        record_activity(request, value, "fare submission", fare, f"{value.title()} fare submission #{fare.pk}")
        return Response(self.get_serializer(fare).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(request, FareStatus.APPROVED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._set_status(request, FareStatus.REJECTED)


class UserAdminViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [f for f in ("username", "email", "profile__full_name") if f.split("__")[0] in USER_FIELDS]
    ordering = ("-date_joined",) if "date_joined" in USER_FIELDS else ("-pk",)

    def get_serializer_class(self):
        return UserAdminUpdateSerializer if self.action in ("update", "partial_update") else UserAdminSerializer

    def get_queryset(self):
        queryset = User.objects.all().select_related("profile")
        state = self.request.query_params.get("blocked")
        if state in ("true", "false"):
            queryset = queryset.filter(is_active=(state == "false"))
        return queryset

    def _refuse(self, request, target):
        if target.pk == request.user.pk:
            return Response({"detail": "You cannot change your own account."}, status=400)
        if target.is_staff or target.is_superuser:
            return Response({"detail": "Staff accounts cannot be changed here."}, status=403)
        return None

    def update(self, request, *args, **kwargs):
        target = self.get_object()
        refused = self._refuse(request, target)
        if refused: return refused
        serializer = self.get_serializer(target, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        target = self.get_queryset().get(pk=target.pk)
        record_activity(request, "updated", "user", target, f"Updated user account: {target.username}")
        return Response(UserAdminSerializer(target, context=self.get_serializer_context()).data)

    def _set_active(self, request, active):
        target = self.get_object()
        refused = self._refuse(request, target)
        if refused: return refused
        target.is_active = active
        target.save(update_fields=["is_active"])
        action_name = "unblocked" if active else "blocked"
        record_activity(request, action_name, "user", target, f"{action_name.title()} user: {target.username}")
        return Response(UserAdminSerializer(target).data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None): return self._set_active(request, False)

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None): return self._set_active(request, True)

    def destroy(self, request, *args, **kwargs):
        target = self.get_object()
        refused = self._refuse(request, target)
        if refused: return refused
        username, pk = target.username, target.pk
        target.delete()
        record_activity(request, "deleted", "user", type("Deleted", (), {"pk": pk})(), f"Deleted user: {username}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActivityLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = AdminActivityLog.objects.select_related("actor").all()
    serializer_class = AdminActivityLogSerializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["actor__username", "action", "entity", "summary"]
    ordering_fields = ["created_at", "action", "entity"]
    ordering = ["-created_at"]


class StatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            "places": Place.objects.count(),
            "pending_places": Place.objects.filter(status=PENDING).count() if HAS_STATUS else None,
            "users": User.objects.count(),
            "blocked_users": User.objects.filter(is_active=False).count(),
            "moderation_enabled": HAS_STATUS,
            "locations": Location.objects.count(),
            "pending_locations": Location.objects.filter(status=LocationStatus.PENDING).count(),
            "approved_locations": Location.objects.filter(status=LocationStatus.APPROVED).count(),
            "rejected_locations": Location.objects.filter(status=LocationStatus.REJECTED).count(),
            "transport_modes": TransportMode.objects.count(),
            "active_transport_modes": TransportMode.objects.filter(is_active=True).count(),
            "fare_submissions": FareSubmission.objects.count(),
            "pending_fares": FareSubmission.objects.filter(status=FareStatus.PENDING).count(),
            "approved_fares": FareSubmission.objects.filter(status=FareStatus.APPROVED).count(),
            "rejected_fares": FareSubmission.objects.filter(status=FareStatus.REJECTED).count(),
        })
