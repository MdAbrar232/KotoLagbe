
import mimetypes

from django.core import signing
from django.db import models
from django.db.models import Avg, Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import (
    AllowAny,
    BasePermission,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Place,
    PlaceItem,
    ItemPriceSubmission,
    ItemStatus,
    PlaceReview,
    PlacePhoto,
    Favorite,
)

from .serializers import (
    PLACE_PHOTO_URL_SALT,
    PlaceSerializer,
    PlaceItemSerializer,
    SuggestPlaceItemSerializer,
    ItemPriceSubmissionSerializer,
    PlaceReviewSerializer,
    PlacePhotoSerializer,
    FavoriteCreateSerializer,
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


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
        )

class PlaceListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PlaceSerializer
    permission_classes = [IsAdminOrReadOnly]

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
                queryset = queryset.filter(
    location_id=location_id,
    location__status="approved",
)
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
            try:
                place_id = int(place.strip())
                if place_id <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValidationError({
                    "place": "Provide a valid place ID."
                })

            queryset = queryset.filter(place_id=place_id)

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


class PlacePhotoListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PlacePhotoSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_place(self):
        return get_object_or_404(Place, pk=self.kwargs["place_id"])

    def get_queryset(self):
        return PlacePhoto.objects.filter(
            place=self.get_place(),
            status=ItemStatus.APPROVED,
        ).select_related("place", "submitted_by")

    def perform_create(self, serializer):
        serializer.save(
            place=self.get_place(),
            submitted_by=self.request.user,
            status=ItemStatus.PENDING,
        )


class PlacePhotoImageAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        photo = get_object_or_404(PlacePhoto, pk=pk)
        is_contributor = (
            request.user.is_authenticated
            and photo.submitted_by_id == request.user.pk
        )
        is_staff = request.user.is_authenticated and request.user.is_staff
        has_private_access = is_contributor or is_staff

        if photo.status != ItemStatus.APPROVED and not has_private_access:
            token = request.query_params.get("token", "")
            try:
                token_data = signing.loads(
                    token,
                    salt=PLACE_PHOTO_URL_SALT,
                    max_age=900,
                )
            except signing.BadSignature:
                raise PermissionDenied("This photo is not publicly available.")

            if token_data.get("photo_id") != photo.pk:
                raise PermissionDenied("This photo is not publicly available.")

        if not photo.image or not photo.image.storage.exists(photo.image.name):
            raise NotFound("The photo file is unavailable.")

        try:
            image_file = photo.image.open("rb")
        except OSError:
            raise NotFound("The photo file is unavailable.")

        content_type = mimetypes.guess_type(photo.image.name)[0] or "application/octet-stream"
        response = FileResponse(image_file, content_type=content_type)
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "no-store"
        return response


class MyPlacePhotoListAPIView(generics.ListAPIView):
    serializer_class = PlacePhotoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PlacePhoto.objects.filter(
            place_id=self.kwargs["place_id"],
            submitted_by=self.request.user,
        ).select_related("place", "submitted_by")


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


class MyPlaceReviewAPIView(generics.RetrieveAPIView):
    serializer_class = PlaceReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            PlaceReview.objects.select_related("place", "user"),
            place_id=self.kwargs["place_id"],
            user=self.request.user,
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


class FavoriteListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return places_with_ratings().filter(
            favorites__user=self.request.user
        ).distinct()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FavoriteCreateSerializer
        return PlaceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save()

        return Response(
            {
                "id": favorite.id,
                "place": favorite.place_id,
                "message": "Place added to favorites.",
            },
            status=201,
        )


class FavoriteDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, place_id):
        favorite = get_object_or_404(
            Favorite,
            user=request.user,
            place_id=place_id,
        )

        favorite.delete()

        return Response(
            {"message": "Place removed from favorites."},
            status=200,
        )
