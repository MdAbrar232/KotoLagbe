from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import FareStatus, FareSubmission, Location, TransportMode


class TransportApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.member = users.create_user("rider", password="test-transport-member")
        cls.a = Location.objects.create(name="Stop A", area="Test area", latitude="23.700000", longitude="90.123456")
        cls.b = Location.objects.create(name="Stop B", area="Test area", latitude="23.710000", longitude="90.223456")
        cls.bus = TransportMode.objects.get(name="Bus")

    def fare_data(self):
        return {"origin": self.a.pk, "destination": self.b.pk, "transport_mode": self.bus.pk, "fare": "35.50"}

    def test_public_coordinates_and_modes(self):
        locations = self.client.get(reverse("transport:location-list")).json()
        self.assertEqual(locations[0], {
            "id": self.a.pk, "name": "Stop A", "area": "Test area", "description": "",
            "latitude": 23.7, "longitude": 90.123456,
        })
        self.assertEqual(self.client.get(reverse("transport:location-detail", args=[self.a.pk])).json(), locations[0])
        modes = self.client.get(reverse("transport:mode-list")).json()
        self.assertTrue({"Rickshaw", "CNG", "Bus", "Leguna"}.issubset({m["name"] for m in modes}))

    def test_coordinate_validation_and_read_only_locations(self):
        stop = Location(name="Edge", area="Test area", latitude="-90.000000", longitude="180.000000")
        stop.full_clean()
        for field, value in [
            ("latitude", "-90.000001"), ("latitude", "90.000001"),
            ("longitude", "-180.000001"), ("longitude", "180.000001"),
            ("latitude", "1.1234567"), ("longitude", None),
        ]:
            with self.subTest(field=field, value=value):
                original = getattr(stop, field)
                setattr(stop, field, value)
                with self.assertRaises(ValidationError) as invalid:
                    stop.full_clean()
                self.assertIn(field, invalid.exception.message_dict)
                setattr(stop, field, original)
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.post(reverse("transport:location-list"), {}).status_code, 405)
        detail = reverse("transport:location-detail", args=[self.a.pk])
        self.assertEqual(self.client.patch(detail, {"area": "New area"}).status_code, 405)
        self.assertEqual(self.client.post(reverse("transport:mode-list"), {"name": "New"}).status_code, 405)

    def test_submission_uses_the_signed_in_user_and_starts_pending(self):
        fares = reverse("transport:fare-list")
        self.assertEqual(self.client.post(fares, self.fare_data(), format="json").status_code, 401)
        login = self.client.post(reverse("login"), {"username": "rider", "password": "test-transport-member"}, format="json")
        self.assertEqual(login.status_code, 200, login.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        body = {**self.fare_data(), "status": "approved", "submitted_by": self.member.pk + 100,
                "submitted_at": "2000-01-01T00:00:00Z"}
        submitted = self.client.post(fares, body, format="json")
        self.assertEqual(submitted.status_code, 201, submitted.data)
        receipt = submitted.json()
        self.assertEqual((receipt["status"], receipt["submitted_by"], receipt["fare"]), ("pending", self.member.pk, "35.50"))
        self.assertNotEqual(receipt["submitted_at"], body["submitted_at"])
        self.client.credentials()
        self.assertEqual(self.client.get(fares).json(), [])

    def test_public_fare_search_only_returns_approved_rows(self):
        url = reverse("transport:fare-list")
        rows = {"origin": self.a, "destination": self.b, "transport_mode": self.bus, "fare": "35.50"}
        approved = FareSubmission.objects.create(**rows, status=FareStatus.APPROVED)
        FareSubmission.objects.create(**rows, status=FareStatus.REJECTED)
        FareSubmission.objects.create(**rows, status=FareStatus.PENDING)
        route = {"origin": self.a.pk, "destination": self.b.pk, "transport_mode": self.bus.pk}
        for filters in ({}, route, {"status": "pending"}, {"status": "rejected"}):
            with self.subTest(filters=filters):
                self.assertEqual([row["id"] for row in self.client.get(url, filters).json()], [approved.pk])
        self.assertEqual(self.client.get(url, {"origin": self.b.pk}).json(), [])
        self.assertEqual(self.client.get(url, {"origin": "invalid"}).status_code, 400)

    def test_invalid_route_or_fare_returns_field_error(self):
        self.client.force_authenticate(self.member)
        for field, value in [
            ("destination", self.a.pk), ("transport_mode", -1),
            ("fare", "0"), ("fare", "-1"), ("fare", "1.005"),
        ]:
            with self.subTest(field=field, value=value):
                body = {**self.fare_data(), field: value}
                response = self.client.post(reverse("transport:fare-list"), body, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertFalse(FareSubmission.objects.exists())

    def test_database_constraints_also_apply_to_orm_writes(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Location.objects.filter(pk=self.a.pk).update(latitude=91)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Location.objects.filter(pk=self.a.pk).update(longitude=-181)
        valid = {
            "origin": self.a, "destination": self.b, "transport_mode": self.bus,
            "fare": 40, "submitted_by": self.member, "status": FareStatus.PENDING,
        }
        for invalid in ({"destination": self.a}, {"fare": 0}, {"status": "other"}):
            with self.subTest(invalid=invalid), self.assertRaises(IntegrityError), transaction.atomic():
                FareSubmission.objects.create(**{**valid, **invalid})
