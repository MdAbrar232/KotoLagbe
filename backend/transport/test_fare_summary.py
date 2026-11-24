from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    FareStatus,
    FareSubmission,
    Location,
    LocationStatus,
    TransportMode,
)


class RouteFareSummaryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.origin = Location.objects.create(
            name="Dhanmondi",
            area="Dhaka",
            latitude="23.746000",
            longitude="90.376000",
            status=LocationStatus.APPROVED,
        )

        cls.destination = Location.objects.create(
            name="Farmgate",
            area="Dhaka",
            latitude="23.757000",
            longitude="90.389000",
            status=LocationStatus.APPROVED,
        )

        cls.bus, _ = TransportMode.objects.get_or_create(
            name="Bus"
        )

        cls.cng, _ = TransportMode.objects.get_or_create(
            name="CNG"
        )

        cls.inactive_mode = TransportMode.objects.create(
            name="Inactive Test Mode",
            is_active=False,
        )

    def create_fare(
        self,
        mode,
        fare,
        route_origin=None,
        route_destination=None,
        fare_status=FareStatus.APPROVED,
    ):
        return FareSubmission.objects.create(
            origin=route_origin or self.origin,
            destination=route_destination or self.destination,
            transport_mode=mode,
            fare=Decimal(str(fare)),
            status=fare_status,
        )

    def get_summary(self, params=None):
        return self.client.get(
            reverse("transport:fare-summary"),
            params or {
                "origin": self.origin.pk,
                "destination": self.destination.pk,
            },
        )

    def test_summary_calculates_fares_per_transport_mode(self):
        self.create_fare(self.bus, "20.00")
        self.create_fare(self.bus, "30.00")
        self.create_fare(self.bus, "100.00", fare_status=FareStatus.PENDING)
        self.create_fare(self.bus, "200.00", fare_status=FareStatus.REJECTED)

        self.create_fare(self.cng, "100.00")
        self.create_fare(self.cng, "140.00")

        response = self.get_summary()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["origin"]["name"], "Dhanmondi")
        self.assertEqual(response.data["destination"]["name"], "Farmgate")

        options = {
            row["transport_mode"]: row
            for row in response.data["transport_options"]
        }

        self.assertEqual(
            options["Bus"],
            {
                "transport_mode": "Bus",
                "average_fare": "25.00",
                "minimum_fare": "20.00",
                "maximum_fare": "30.00",
                "submission_count": 2,
            },
        )

        self.assertEqual(
            options["CNG"],
            {
                "transport_mode": "CNG",
                "average_fare": "120.00",
                "minimum_fare": "100.00",
                "maximum_fare": "140.00",
                "submission_count": 2,
            },
        )

    def test_inactive_transport_modes_are_excluded(self):
        self.create_fare(self.inactive_mode, "50.00")

        response = self.get_summary()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["transport_options"], [])

    def test_reverse_direction_is_a_separate_route(self):
        self.create_fare(
            self.bus,
            "35.00",
            route_origin=self.destination,
            route_destination=self.origin,
        )

        response = self.get_summary()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["transport_options"], [])

    def test_both_route_parameters_are_required(self):
        response = self.client.get(
            reverse("transport:fare-summary"),
            {"origin": self.origin.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("destination", response.data)

    def test_same_origin_and_destination_is_rejected(self):
        response = self.get_summary({
            "origin": self.origin.pk,
            "destination": self.origin.pk,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("destination", response.data)

    def test_unapproved_location_cannot_be_used(self):
        pending = Location.objects.create(
            name="Pending Stop",
            area="Dhaka",
            latitude="23.720000",
            longitude="90.320000",
            status=LocationStatus.PENDING,
        )

        response = self.get_summary({
            "origin": self.origin.pk,
            "destination": pending.pk,
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)