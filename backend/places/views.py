from django.db import models
from rest_framework import generics
from .models import Place
from .serializers import PlaceSerializer


class PlaceListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        queryset = Place.objects.all()

        # Search by name, area, or address
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(area__icontains=search)
                | models.Q(address__icontains=search)
            )

        # Filter by category
        category = self.request.query_params.get("category", "").strip()
        if category:
            queryset = queryset.filter(category__iexact=category)

        # Sort by average price
        ordering = self.request.query_params.get("ordering", "")
        if ordering in ("price", "-price"):
            queryset = queryset.order_by(
                "average_price" if ordering == "price" else "-average_price"
            )
        else:
            queryset = queryset.order_by("name")

        return queryset

class PlaceDetailAPIView(generics.RetrieveAPIView):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer