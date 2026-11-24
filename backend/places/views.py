from django.db import models
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    AllowAny,
    BasePermission,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)

from .models import (
    Place,
    PlaceItem,
    ItemPriceSubmission,
    ItemStatus,
    PlaceReview,
)

from .serializers import (
    PlaceSerializer,
    PlaceItemSerializer,
    SuggestPlaceItemSerializer,
    ItemPriceSubmissionSerializer,
    PlaceReviewSerializer,
)


class IsReviewOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return (
            request.user.is_authenticated
            and obj.user_id == request.user.pk
        )


def places_with_ratings():
    return Place.objects.select_related(
        "location",
        "parent",
    ).annotate(
        average_rating=Avg(
            "reviews__rating",
            filter=Q(reviews__status=ItemStatus.APPROVED),
        ),
        review_count=Count(
            "reviews",
            filter=Q(reviews__status=ItemStatus.APPROVED),
        ),
    )


class PlaceListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        queryset = places_with_ratings()
        params = self.request.query_params

        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(area__icontains=search)
                | models.Q(address__icontains=search)
            )

        category = params.get("category", "").strip()
        if category:
            queryset = queryset.filter(category__iexact=category)

        parent = params.get("parent", "").strip()
        if parent:
            if parent.lower() == "null":
                queryset = queryset.filter(parent__isnull=True)
            else:
                try:
                    parent_id = int(parent)
                    queryset = queryset.filter(parent_id=parent_id)
                except ValueError:
                    raise ValidationError({
                        "parent": "Provide a valid parent ID or 'null'."
                    })

        location = params.get("location", "").strip()
        if location:
            try:
                location_id = int(location)
                queryset = queryset.filter(location_id=location_id)
            except ValueError:
                raise ValidationError({
                    "location": "Provide a valid location ID."
                })

        ordering = params.get("ordering", "")
        if ordering in ("price", "-price"):
            queryset = queryset.order_by(
                "average_price" if ordering == "price"
                else "-average_price"
            )
        elif ordering in ("rating", "-rating"):
            queryset = queryset.order_by(
                "average_rating" if ordering == "rating"
                else "-average_rating"
            )
        else:
            queryset = queryset.order_by("name")

        return queryset


class PlaceDetailAPIView(generics.RetrieveAPIView):
    queryset = places_with_ratings()
    serializer_class = PlaceSerializer


class PlaceItemListAPIView(generics.ListAPIView):
    serializer_class = PlaceItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = PlaceItem.objects.filter(
            status=ItemStatus.APPROVED
        ).select_related("place").annotate(
            average_price=Avg(
                "price_submissions__price",
                filter=Q(
                    price_submissions__status=ItemStatus.APPROVED
                ),
            )
        )

        place = self.request.query_params.get("place")
        search = self.request.query_params.get("search", "").strip()
        category = self.request.query_params.get("category", "").strip()

        if place:
            queryset = queryset.filter(place_id=place)

        if search:
            queryset = queryset.filter(name__icontains=search)

        if category:
            queryset = queryset.filter(category__iexact=category)

        return queryset.order_by("name")


class SuggestPlaceItemAPIView(generics.CreateAPIView):
    serializer_class = SuggestPlaceItemSerializer
    permission_classes = [IsAuthenticated]


class ItemPriceSubmissionListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ItemPriceSubmissionSerializer

    def get_item(self):
        return get_object_or_404(
            PlaceItem,
            pk=self.kwargs["item_id"],
            status=ItemStatus.APPROVED,
        )

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return ItemPriceSubmission.objects.filter(
            item=self.get_item(),
            status=ItemStatus.APPROVED,
        ).select_related("submitted_by")

    def perform_create(self, serializer):
        serializer.save(
            item=self.get_item(),
            submitted_by=self.request.user,
        )


class PlaceReviewListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PlaceReviewSerializer

    def get_place(self):
        return get_object_or_404(
            Place,
            pk=self.kwargs["place_id"],
        )

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return PlaceReview.objects.filter(
            place=self.get_place(),
            status=ItemStatus.APPROVED,
        ).select_related("user")

    def perform_create(self, serializer):
        place = self.get_place()

        if PlaceReview.objects.filter(
            place=place,
            user=self.request.user,
        ).exists():
            raise ValidationError({
                "detail": "You have already reviewed this place."
            })

        serializer.save(
            place=place,
            user=self.request.user,
            status=ItemStatus.PENDING,
        )


class PlaceReviewDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PlaceReviewSerializer
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsReviewOwnerOrReadOnly,
    ]

    def get_queryset(self):
        queryset = PlaceReview.objects.select_related(
            "place",
            "user",
        ).filter(place_id=self.kwargs["place_id"])

        if self.request.user.is_authenticated:
            return queryset.filter(
                Q(status=ItemStatus.APPROVED)
                | Q(user=self.request.user)
            )

        return queryset.filter(status=ItemStatus.APPROVED)

    def perform_update(self, serializer):
        serializer.save(
            status=ItemStatus.PENDING,
            reviewed_by=None,
            reviewed_at=None,
            rejection_reason="",
        )