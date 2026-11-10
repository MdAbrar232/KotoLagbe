from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PlaceAdminViewSet, StatsView, UserAdminViewSet

router = DefaultRouter()
router.register("places", PlaceAdminViewSet, basename="admin-places")
router.register("users", UserAdminViewSet, basename="admin-users")

urlpatterns = [
    path("stats/", StatsView.as_view(), name="admin-stats"),
    path("", include(router.urls)),
]
