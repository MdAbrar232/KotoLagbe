
from django.urls import path

from .views import (
    PlaceListCreateAPIView,
    PlaceDetailAPIView,
    PlaceItemListAPIView,
    SuggestPlaceItemAPIView,
    ItemPriceSubmissionListCreateAPIView,
    PlaceReviewListCreateAPIView,
    PlaceReviewDetailAPIView,
    MyPlaceReviewAPIView,
    FavoriteListCreateAPIView,
    FavoriteDeleteAPIView,
)


urlpatterns = [
    path("", PlaceListCreateAPIView.as_view(), name="place-list-create"),
    path("<int:pk>/", PlaceDetailAPIView.as_view(), name="place-detail"),

    path("favorites/", FavoriteListCreateAPIView.as_view(), name="favorite-list-create"),
    path(
        "favorites/<int:place_id>/",
        FavoriteDeleteAPIView.as_view(),
        name="favorite-delete",
    ),

    path("items/", PlaceItemListAPIView.as_view(), name="item-list"),
    path("items/suggest/", SuggestPlaceItemAPIView.as_view(), name="item-suggest"),

    path(
        "items/<int:item_id>/prices/",
        ItemPriceSubmissionListCreateAPIView.as_view(),
        name="item-price-list-create",
    ),

    path(
        "<int:place_id>/reviews/",
        PlaceReviewListCreateAPIView.as_view(),
        name="place-review-list-create",
    ),
    path(
        "<int:place_id>/reviews/mine/",
        MyPlaceReviewAPIView.as_view(),
        name="my-place-review",
    ),
    path(
        "<int:place_id>/reviews/<int:pk>/",
        PlaceReviewDetailAPIView.as_view(),
        name="place-review-detail",
    ),
]
