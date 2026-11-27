
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

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
    PlacePhotoModerationViewSet,
)
from .review_views import PlaceReviewModerationViewSet
from .permissions import IsAdmin


router = DefaultRouter()

router.register("places", PlaceAdminViewSet, basename="admin-places")
router.register("users", UserAdminViewSet, basename="admin-users")
router.register("locations", LocationAdminViewSet, basename="admin-locations")
router.register(
    "transport-modes",
    TransportModeAdminViewSet,
    basename="admin-transport-modes",
)
router.register("fares", FareAdminViewSet, basename="admin-fares")
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
router.register(
    "photos",
    PlacePhotoModerationViewSet,
    basename="admin-photos",
)


class AdminAPIRootView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        return Response({
            "stats": reverse("admin-stats", request=request),
            "places": reverse("admin-places-list", request=request),
            "users": reverse("admin-users-list", request=request),
            "locations": reverse("admin-locations-list", request=request),
            "transport-modes": reverse(
                "admin-transport-modes-list", request=request
            ),
            "fares": reverse("admin-fares-list", request=request),
            "items": reverse("admin-items-list", request=request),
            "item-prices": reverse(
                "admin-item-prices-list", request=request
            ),
            "reviews": reverse("admin-reviews-list", request=request),
            "photos": reverse("admin-photos-list", request=request),
            "activity": reverse("admin-activity-list", request=request),
        })


urlpatterns = [
    path("stats/", StatsView.as_view(), name="admin-stats"),
    path("", AdminAPIRootView.as_view(), name="admin-root"),
    path("", include(router.urls)),
]
