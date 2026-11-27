from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .permissions import IsAdmin
from .views import (
    ActivityLogViewSet,
    FareAdminViewSet,
    LocationAdminViewSet,
    PlaceAdminViewSet,
    StatsView,
    TransportModeAdminViewSet,
    UserAdminViewSet,
    PlaceItemModerationViewSet,
    ItemPriceModerationViewSet,
)

from .review_views import PlaceReviewModerationViewSet, PlacePhotoModerationViewSet


class AdministrationRouter(DefaultRouter):
    class APIRootView(DefaultRouter.APIRootView):
        permission_classes = [IsAdmin]


router = AdministrationRouter()

router.register("places", PlaceAdminViewSet, basename="admin-places")
router.register("users", UserAdminViewSet, basename="admin-users")
router.register("locations", LocationAdminViewSet, basename="admin-locations")
router.register(
    "transport-modes",
    TransportModeAdminViewSet,
    basename="admin-transport-modes",
)
router.register("fares", FareAdminViewSet, basename="admin-fares")
router.register("photos", PlacePhotoModerationViewSet, basename="admin-photos")
router.register("activity", ActivityLogViewSet, basename="admin-activity")

router.register(
    "items",
    PlaceItemModerationViewSet,
    basename="admin-items",
)
router.register(
    "item-prices",
    ItemPriceModerationViewSet,
    basename="admin-item-prices",
)
router.register(
    "reviews",
    PlaceReviewModerationViewSet,
    basename="admin-reviews",
)


urlpatterns = [
    path("stats/", StatsView.as_view(), name="admin-stats"),
    path("", include(router.urls)),
]