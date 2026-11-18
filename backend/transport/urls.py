from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import FareListCreate, LocationViewSet, TransportModeList

app_name = "transport"
router = SimpleRouter()
router.register("locations", LocationViewSet, basename="location")

urlpatterns = router.urls + [
    path("modes/", TransportModeList.as_view(), name="mode-list"),
    path("fares/", FareListCreate.as_view(), name="fare-list"),
]
