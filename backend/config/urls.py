from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/places/", include("places.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/admin/", include("administration.urls")),
]