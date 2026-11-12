
from rest_framework import generics, status
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import UserProfile, StatusPost
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer,
    StatusPostSerializer,
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
