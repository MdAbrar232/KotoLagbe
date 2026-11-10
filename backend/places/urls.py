from django.urls import path
from .views import PlaceListCreateAPIView, PlaceDetailAPIView

urlpatterns = [
    path("", PlaceListCreateAPIView.as_view(), name="place-list-create"),
    path("<int:pk>/", PlaceDetailAPIView.as_view(), name="place-detail"),
]