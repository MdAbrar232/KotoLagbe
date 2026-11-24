from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from places.models import (
    Place,
    PlaceItem,
    ItemPriceSubmission,
    ItemStatus,
)
from transport.models import (
    Location,
    LocationStatus,
    TransportMode,
    FareSubmission,
    FareStatus,
)


class SubmissionHistoryTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.user = User.objects.create_user(
            username="contributor",
            password="test-password-123",
        )

        cls.other_user = User.objects.create_user(
            username="another_contributor",
            password="test-password-456",
        )

        cls.origin = Location.objects.create(
            name="Dhanmondi",
            area="Dhaka",
            latitude="23.746000",
            longitude="90.376000",
            submitted_by=cls.user,
            status=LocationStatus.PENDING,
        )

        cls.destination = Location.objects.create(
            name="Farmgate",
            area="Dhaka",
            latitude="23.757000",
            longitude="90.389000",
            submitted_by=cls.user,
            status=LocationStatus.PENDING,
        )

        cls.bus, _ = TransportMode.objects.get_or_create(
            name="Bus"
        )

        cls.place = Place.objects.create(
            name="Test Restaurant",
            category="restaurant",
            area="Dhanmondi",
            address="Test address",
            description="Test place",
            average_price=Decimal("100.00"),
        )

        cls.item = PlaceItem.objects.create(
            place=cls.place,
            name="Chicken Burger",
            category="food",
            description="Test item",
            submitted_by=cls.user,
            status=ItemStatus.PENDING,
        )

        cls.price = ItemPriceSubmission.objects.create(
            item=cls.item,
            submitted_by=cls.user,
            price=Decimal("250.00"),
            status=ItemStatus.PENDING,
        )

    def history_url(self):
        return reverse("submission-history")

    def test_anonymous_user_cannot_access_history(self):
        response = self.client.get(self.history_url())

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_only_sees_own_submissions(self):
        self.client.force_authenticate(self.user)

        Location.objects.create(
            name="Other User Stop",
            area="Dhaka",
            latitude="23.770000",
            longitude="90.390000",
            submitted_by=self.other_user,
            status=LocationStatus.PENDING,
        )

        response = self.client.get(self.history_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        location_names = [
            row["name"]
            for row in response.data
            if row["type"] == "location"
        ]

        self.assertIn("Dhanmondi", location_names)
        self.assertIn("Farmgate", location_names)
        self.assertNotIn("Other User Stop", location_names)

    def test_history_includes_all_four_submission_types(self):
        FareSubmission.objects.create(
            origin=self.origin,
            destination=self.destination,
            transport_mode=self.bus,
            fare=Decimal("35.00"),
            submitted_by=self.user,
            status=FareStatus.PENDING,
        )

        self.client.force_authenticate(self.user)

        response = self.client.get(self.history_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        submission_types = {
            row["type"]
            for row in response.data
        }

        self.assertEqual(
            submission_types,
            {
                "location",
                "fare",
                "place_item",
                "item_price",
            },
        )

    def test_history_includes_moderation_status(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(self.history_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item_row = next(
            row for row in response.data
            if row["type"] == "place_item"
        )

        price_row = next(
            row for row in response.data
            if row["type"] == "item_price"
        )

        self.assertEqual(item_row["status"], ItemStatus.PENDING)
        self.assertEqual(price_row["status"], ItemStatus.PENDING)

    def test_history_is_ordered_newest_first(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(self.history_url())

        dates = [
            row["submitted_at"]
            for row in response.data
        ]

        self.assertEqual(dates, sorted(dates, reverse=True))