
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import (
    FareStatus,
    FareSubmission,
    Location,
    LocationStatus,
    TransportMode,
)


class TransportApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects

        cls.member = users.create_user(
            "rider",
            password="test-transport-member",
        )

        cls.a = Location.objects.create(
            name="Stop A",
            area="Test area",
            latitude="23.700000",
            longitude="90.123456",
            status=LocationStatus.APPROVED,
        )

        cls.b = Location.objects.create(
            name="Stop B",
            area="Test area",
            latitude="23.710000",
            longitude="90.223456",
            status=LocationStatus.APPROVED,
        )

        cls.bus = TransportMode.objects.get(name="Bus")

    def fare_data(self):
        return {
            "origin": self.a.pk,
            "destination": self.b.pk,
            "transport_mode": self.bus.pk,
            "fare": "35.50",
        }

    def test_public_coordinates_and_modes(self):
        locations = self.client.get(
            reverse("transport:location-list")
        ).json()

        self.assertEqual(
            locations[0],
            {
                "id": self.a.pk,
                "name": "Stop A",
                "area": "Test area",
                "description": "",
                "latitude": 23.7,
                "longitude": 90.123456,
            },
        )

        detail = reverse(
            "transport:location-detail",
            args=[self.a.pk],
        )

        self.assertEqual(
            self.client.get(detail).json(),
            locations[0],
        )

        modes = self.client.get(
            reverse("transport:mode-list")
        ).json()

        self.assertTrue(
            {"Rickshaw", "CNG", "Bus", "Leguna"}.issubset(
                {mode["name"] for mode in modes}
            )
        )

    def test_coordinate_validation_and_read_only_locations(self):
        stop = Location(
            name="Edge",
            area="Test area",
            latitude="-90.000000",
            longitude="180.000000",
            status=LocationStatus.APPROVED,
        )

        stop.full_clean()

        for field, value in [
            ("latitude", "-90.000001"),
            ("latitude", "90.000001"),
            ("longitude", "-180.000001"),
            ("longitude", "180.000001"),
            ("latitude", "1.1234567"),
            ("longitude", None),
        ]:
            with self.subTest(field=field, value=value):
                original = getattr(stop, field)
                setattr(stop, field, value)

                with self.assertRaises(ValidationError) as invalid:
                    stop.full_clean()

                self.assertIn(
                    field,
                    invalid.exception.message_dict,
                )

                setattr(stop, field, original)

        locations_url = reverse("transport:location-list")

        # Anonymous users cannot submit locations.
        response = self.client.post(
            locations_url,
            {
                "name": "New Stop",
                "area": "Test area",
                "latitude": 23.72,
                "longitude": 90.22,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

        self.client.force_authenticate(self.member)

        # Authenticated users can submit locations.
        response = self.client.post(
            locations_url,
            {
                "name": "New Stop",
                "area": "Test area",
                "description": "A newly submitted location",
                "latitude": 23.72,
                "longitude": 90.22,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

        submitted_location = Location.objects.get(
            name="New Stop"
        )

        self.assertEqual(
            submitted_location.status,
            LocationStatus.PENDING,
        )

        # Pending locations must not appear in the public list.
        public_locations = self.client.get(
            locations_url
        ).json()

        self.assertNotIn(
            submitted_location.pk,
            [location["id"] for location in public_locations],
        )

        # Public location editing is disabled.
        detail_url = reverse(
            "transport:location-detail",
            args=[self.a.pk],
        )

        self.assertEqual(
            self.client.patch(
                detail_url,
                {"area": "New area"},
                format="json",
            ).status_code,
            405,
        )

        # Public transport mode creation is disabled.
        self.assertEqual(
            self.client.post(
                reverse("transport:mode-list"),
                {"name": "New"},
                format="json",
            ).status_code,
            405,
        )

    def test_submission_uses_signed_in_user_and_starts_pending(self):
        fares_url = reverse("transport:fare-list")

        # Anonymous users cannot submit fares.
        response = self.client.post(
            fares_url,
            self.fare_data(),
            format="json",
        )

        self.assertEqual(response.status_code, 401)

        # Sign in using the test account.
        login = self.client.post(
            reverse("login"),
            {
                "username": "rider",
                "password": "test-transport-member",
            },
            format="json",
        )

        self.assertEqual(login.status_code, 200, login.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
        )

        body = {
            **self.fare_data(),
            "status": "approved",
            "submitted_by": self.member.pk + 100,
            "submitted_at": "2000-01-01T00:00:00Z",
        }

        submitted = self.client.post(
            fares_url,
            body,
            format="json",
        )

        self.assertEqual(
            submitted.status_code,
            201,
            submitted.data,
        )

        receipt = submitted.json()

        self.assertEqual(
            (
                receipt["status"],
                receipt["submitted_by"],
                receipt["fare"],
            ),
            (
                "pending",
                self.member.pk,
                "35.50",
            ),
        )

        self.assertNotEqual(
            receipt["submitted_at"],
            body["submitted_at"],
        )

        # Pending fares must not be publicly visible.
        self.client.credentials()

        self.assertEqual(
            self.client.get(fares_url).json(),
            [],
        )

    def test_pending_or_rejected_locations_cannot_be_used_for_fares(self):
        pending = Location.objects.create(
            name="Pending Stop",
            area="Test area",
            latitude="23.720000",
            longitude="90.320000",
            status=LocationStatus.PENDING,
        )

        rejected = Location.objects.create(
            name="Rejected Stop",
            area="Test area",
            latitude="23.730000",
            longitude="90.330000",
            status=LocationStatus.REJECTED,
        )

        self.client.force_authenticate(self.member)

        fares_url = reverse("transport:fare-list")

        invalid_routes = [
            {
                **self.fare_data(),
                "origin": pending.pk,
            },
            {
                **self.fare_data(),
                "destination": pending.pk,
            },
            {
                **self.fare_data(),
                "origin": rejected.pk,
            },
            {
                **self.fare_data(),
                "destination": rejected.pk,
            },
        ]

        for body in invalid_routes:
            with self.subTest(body=body):
                response = self.client.post(
                    fares_url,
                    body,
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    400,
                    response.data,
                )

        self.assertFalse(FareSubmission.objects.exists())

    def test_public_fare_search_only_returns_approved_rows(self):
        fares_url = reverse("transport:fare-list")

        rows = {
            "origin": self.a,
            "destination": self.b,
            "transport_mode": self.bus,
            "fare": "35.50",
        }

        approved = FareSubmission.objects.create(
            **rows,
            status=FareStatus.APPROVED,
        )

        FareSubmission.objects.create(
            **rows,
            status=FareStatus.REJECTED,
        )

        FareSubmission.objects.create(
            **rows,
            status=FareStatus.PENDING,
        )

        route = {
            "origin": self.a.pk,
            "destination": self.b.pk,
            "transport_mode": self.bus.pk,
        }

        for filters in (
            {},
            route,
            {"status": "pending"},
            {"status": "rejected"},
        ):
            with self.subTest(filters=filters):
                response = self.client.get(
                    fares_url,
                    filters,
                )

                self.assertEqual(
                    [row["id"] for row in response.json()],
                    [approved.pk],
                )

        self.assertEqual(
            self.client.get(
                fares_url,
                {"origin": self.b.pk},
            ).json(),
            [],
        )

        self.assertEqual(
            self.client.get(
                fares_url,
                {"origin": "invalid"},
            ).status_code,
            400,
        )

    def test_invalid_route_or_fare_returns_field_error(self):
        self.client.force_authenticate(self.member)

        fares_url = reverse("transport:fare-list")

        invalid_values = [
            ("destination", self.a.pk),
            ("transport_mode", -1),
            ("fare", "0"),
            ("fare", "-1"),
            ("fare", "1.005"),
        ]

        for field, value in invalid_values:
            with self.subTest(field=field, value=value):
                body = {
                    **self.fare_data(),
                    field: value,
                }

                response = self.client.post(
                    fares_url,
                    body,
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    400,
                    response.data,
                )

                self.assertIn(
                    field,
                    response.json(),
                )

        self.assertFalse(FareSubmission.objects.exists())

    def test_database_constraints_also_apply_to_orm_writes(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Location.objects.filter(
                pk=self.a.pk
            ).update(latitude=91)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Location.objects.filter(
                pk=self.a.pk
            ).update(longitude=-181)

        valid = {
            "origin": self.a,
            "destination": self.b,
            "transport_mode": self.bus,
            "fare": 40,
            "submitted_by": self.member,
            "status": FareStatus.PENDING,
        }

        invalid_records = [
            {"destination": self.a},
            {"fare": 0},
            {"status": "other"},
        ]

        for invalid in invalid_records:
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                FareSubmission.objects.create(
                    **{**valid, **invalid}
                )
