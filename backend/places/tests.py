
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal

from places.models import PlaceItem, ItemPriceSubmission, ItemStatus
from transport.models import Location
from .models import Place


User = get_user_model()


class PlaceAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)

        self.location = Location.objects.create(
            name="Farmgate",
            area="Tejgaon",
            latitude=23.7570,
            longitude=90.3890,
            status="approved",
        )

        self.parent_place = Place.objects.create(
            name="Shopping Mall",
            category="Mall",
            area="Farmgate",
            location=self.location,
        )

        self.child_place = Place.objects.create(
            name="Food Court",
            category="Restaurant",
            area="Farmgate",
            location=self.location,
            parent=self.parent_place,
        )

    def test_filter_by_parent(self):
        response = self.client.get(
            "/api/places/",
            {"parent": self.parent_place.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_top_level_places(self):
        response = self.client.get(
            "/api/places/",
            {"parent": "null"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_location(self):
        response = self.client.get(
            "/api/places/",
            {"location": self.location.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_parent_filter(self):
        response = self.client.get(
            "/api/places/",
            {"parent": "invalid"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_place_cannot_be_its_own_parent(self):
        from places.serializers import PlaceSerializer

        serializer = PlaceSerializer(
            instance=self.parent_place,
            data={"parent": self.parent_place.id},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("parent", serializer.errors)

    def test_place_cannot_be_parent_of_its_own_ancestor(self):
        from places.serializers import PlaceSerializer

        # Food Court is already a child of Shopping Mall.
        # Making Shopping Mall a child of Food Court creates a cycle.
        serializer = PlaceSerializer(
            instance=self.parent_place,
            data={"parent": self.child_place.id},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("parent", serializer.errors)

    def test_authenticated_user_can_suggest_item_with_price(self):
        response = self.client.post(
            "/api/places/items/suggest/",
            {
                "place": self.parent_place.id,
                "name": "Chicken Burger",
                "category": "Food",
                "description": "Grilled chicken burger",
                "price": "250.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        item = PlaceItem.objects.get(name="Chicken Burger")
        price = ItemPriceSubmission.objects.get(item=item)

        self.assertEqual(item.status, ItemStatus.PENDING)
        self.assertEqual(price.status, ItemStatus.PENDING)
        self.assertEqual(price.price, Decimal("250.00"))

    def test_unauthenticated_user_cannot_suggest_item(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/places/items/suggest/",
            {
                "place": self.parent_place.id,
                "name": "Pizza",
                "category": "Food",
                "price": "300.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(PlaceItem.objects.count(), 0)

    def test_pending_items_are_not_publicly_visible(self):
        item = PlaceItem.objects.create(
            place=self.parent_place,
            name="Pending Burger",
            category="Food",
            submitted_by=self.user,
            status=ItemStatus.PENDING,
        )

        response = self.client.get("/api/places/items/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            item.id,
            [entry["id"] for entry in response.data],
        )

    def test_average_price_uses_approved_submissions_only(self):
        item = PlaceItem.objects.create(
            place=self.parent_place,
            name="Kacchi",
            category="Food",
            submitted_by=self.user,
            status=ItemStatus.APPROVED,
        )

        ItemPriceSubmission.objects.create(
            item=item,
            submitted_by=self.user,
            price=Decimal("400.00"),
            status=ItemStatus.APPROVED,
        )

        ItemPriceSubmission.objects.create(
            item=item,
            submitted_by=self.user,
            price=Decimal("500.00"),
            status=ItemStatus.APPROVED,
        )

        ItemPriceSubmission.objects.create(
            item=item,
            submitted_by=self.user,
            price=Decimal("900.00"),
            status=ItemStatus.PENDING,
        )

        response = self.client.get("/api/places/items/")

        self.assertEqual(response.status_code, 200)

        kacchi = next(
            entry for entry in response.data
            if entry["id"] == item.id
        )

        self.assertEqual(
            Decimal(str(kacchi["average_price"])),
            Decimal("450.00"),
        )
