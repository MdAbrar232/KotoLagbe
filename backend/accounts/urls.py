
from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    MyProfileView,
    StatusPostListCreateView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),

    path("login/", LoginView.as_view(), name="login"),

    path("profile/", MyProfileView.as_view(), name="my-profile"),

    path("posts/", StatusPostListCreateView.as_view(), name="status-posts"),
]
