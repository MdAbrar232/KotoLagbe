from django.apps import apps
from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAdmin
from .serializers import PlaceAdminSerializer, UserAdminSerializer

Place = apps.get_model("places", "Place")
User = get_user_model()

PLACE_FIELDS = {f.name for f in Place._meta.get_fields()}
USER_FIELDS = {f.name for f in User._meta.get_fields()}

# Moderation is optional. It switches on automatically when Place has a `status` field.
HAS_STATUS = "status" in PLACE_FIELDS
PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"


class PlaceAdminViewSet(viewsets.ModelViewSet):
    """Admin CRUD for places: list (incl. pending), edit, delete, approve, reject."""

    serializer_class = PlaceAdminSerializer
    permission_classes = [IsAdmin]
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
            return Response(
                {"detail": "Place has no 'status' field, so approval is not enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        place = self.get_object()
        place.status = value
        place.save(update_fields=["status"])
        return Response(self.get_serializer(place).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(APPROVED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._set_status(REJECTED)


class UserAdminViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin view of accounts: list, block, unblock, delete."""

    serializer_class = UserAdminSerializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [f for f in ("username", "email") if f in USER_FIELDS]
    ordering = ("-date_joined",) if "date_joined" in USER_FIELDS else ("-pk",)

    def get_queryset(self):
        queryset = User.objects.all()
        state = self.request.query_params.get("blocked")
        if state in ("true", "false"):
            queryset = queryset.filter(is_active=(state == "false"))
        return queryset

    def _refuse(self, request, target):
        """Admins may not lock themselves out or change other staff accounts."""
        if target.pk == request.user.pk:
            return Response({"detail": "You cannot change your own account."},
                            status=status.HTTP_400_BAD_REQUEST)
        if target.is_staff or target.is_superuser:
            return Response({"detail": "Staff accounts cannot be changed here."},
                            status=status.HTTP_403_FORBIDDEN)
        return None

    def _set_active(self, request, active):
        target = self.get_object()
        refused = self._refuse(request, target)
        if refused:
            return refused
        target.is_active = active
        target.save(update_fields=["is_active"])
        return Response(self.get_serializer(target).data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        return self._set_active(request, False)

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        return self._set_active(request, True)

    def destroy(self, request, *args, **kwargs):
        target = self.get_object()
        refused = self._refuse(request, target)
        if refused:
            return refused
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StatsView(APIView):
    """Counts for the admin dashboard strip."""

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            "places": Place.objects.count(),
            "pending_places": Place.objects.filter(status=PENDING).count() if HAS_STATUS else None,
            "users": User.objects.count(),
            "blocked_users": User.objects.filter(is_active=False).count(),
            "moderation_enabled": HAS_STATUS,
        })
