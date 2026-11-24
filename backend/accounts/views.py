from rest_framework import generics, status
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from places.models import PlaceItem, ItemPriceSubmission
from transport.models import Location, FareSubmission

from .models import UserProfile, StatusPost
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer,
    StatusPostSerializer,
    LocationSubmissionSerializer,
    FareSubmissionHistorySerializer,
    PlaceItemSubmissionSerializer,
    ItemPriceSubmissionHistorySerializer,
)


class RegisterView(generics.CreateAPIView):

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "message": "Registration successful!",
                "username": user.username,
                "email": user.email,
                "full_name": user.profile.full_name,
                "location": user.profile.location,
            },
            status=status.HTTP_201_CREATED
        )


class LoginView(TokenObtainPairView):

    serializer_class = LoginSerializer


class MyProfileView(generics.RetrieveUpdateAPIView):

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):

        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                "full_name": self.request.user.username,
                "location": "",
            }
        )

        return profile


class StatusPostListCreateView(generics.ListCreateAPIView):

    serializer_class = StatusPostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    queryset = StatusPost.objects.select_related(
        "author",
        "author__profile"
    ).all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class SubmissionHistoryView(APIView):
    """
    Returns all contributions made by the authenticated user,
    ordered from newest to oldest.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user
        submissions = []

        location_rows = Location.objects.filter(
            submitted_by=user
        )

        fare_rows = FareSubmission.objects.filter(
            submitted_by=user
        ).select_related(
            "origin",
            "destination",
            "transport_mode",
        )

        item_rows = PlaceItem.objects.filter(
            submitted_by=user
        ).select_related("place")

        price_rows = ItemPriceSubmission.objects.filter(
            submitted_by=user
        ).select_related(
            "item",
            "item__place",
        )

        datasets = [
            (
                location_rows,
                LocationSubmissionSerializer,
                lambda obj: obj.submitted_at,
            ),
            (
                fare_rows,
                FareSubmissionHistorySerializer,
                lambda obj: obj.submitted_at,
            ),
            (
                item_rows,
                PlaceItemSubmissionSerializer,
                lambda obj: obj.created_at,
            ),
            (
                price_rows,
                ItemPriceSubmissionHistorySerializer,
                lambda obj: obj.submitted_at,
            ),
        ]

        for queryset, serializer_class, date_getter in datasets:
            for obj in queryset:
                serialized = serializer_class(obj).data

                submissions.append({
                    "_sort_date": date_getter(obj),
                    "data": serialized,
                })

        submissions.sort(
            key=lambda entry: entry["_sort_date"],
            reverse=True,
        )

        return Response([
            entry["data"]
            for entry in submissions
        ])