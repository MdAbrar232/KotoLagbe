from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityLogViewSet, FareAdminViewSet, LocationAdminViewSet,
    PlaceAdminViewSet, StatsView, TransportModeAdminViewSet, UserAdminViewSet,
)

router = DefaultRouter()
router.register("places", PlaceAdminViewSet, basename="admin-places")
router.register("users", UserAdminViewSet, basename="admin-users")
router.register("locations", LocationAdminViewSet, basename="admin-locations")
router.register("transport-modes", TransportModeAdminViewSet, basename="admin-transport-modes")
router.register("fares", FareAdminViewSet, basename="admin-fares")
router.register("activity", ActivityLogViewSet, basename="admin-activity")

urlpatterns = [path("stats/", StatsView.as_view(), name="admin-stats"), path("", include(router.urls))]
