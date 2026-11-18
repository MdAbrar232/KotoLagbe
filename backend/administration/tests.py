
from django.contrib.auth import get_user_model

from accounts.models import UserProfile
from rest_framework.test import APITestCase

User = get_user_model()


class AdministrationApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "boss", "boss@example.com", "pw12345!", is_staff=True
        )
        self.member = User.objects.create_user(
            "member", "m@example.com", "pw12345!"
        )
        self.other_staff = User.objects.create_user(
            "staff2", "s2@example.com", "pw12345!", is_staff=True
        )

    def test_anonymous_is_rejected(self):
        self.assertIn(
            self.client.get("/api/admin/stats/").status_code,
            (401, 403),
        )

    def test_normal_user_is_rejected(self):
        self.client.force_authenticate(self.member)

        for endpoint in [
            "/api/admin/places/",
            "/api/admin/users/",
            "/api/admin/locations/",
            "/api/admin/transport-modes/",
            "/api/admin/fares/",
            "/api/admin/activity/",
        ]:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(
                    self.client.get(endpoint).status_code,
                    403,
                )

    def test_staff_can_open_dashboard_and_lists(self):
        self.client.force_authenticate(self.admin)

        self.assertEqual(
            self.client.get("/api/admin/stats/").status_code, 200
        )
        self.assertEqual(
            self.client.get("/api/admin/places/").status_code, 200
        )
        self.assertEqual(
            self.client.get("/api/admin/users/").status_code, 200
        )

    def test_block_and_unblock_member(self):
        self.client.force_authenticate(self.admin)

        self.assertEqual(
            self.client.post(
                f"/api/admin/users/{self.member.pk}/block/"
            ).status_code,
            200,
        )

        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)

        self.client.post(
            f"/api/admin/users/{self.member.pk}/unblock/"
        )

        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)

    def test_cannot_block_self_or_other_staff(self):
        self.client.force_authenticate(self.admin)

        self.assertEqual(
            self.client.post(
                f"/api/admin/users/{self.admin.pk}/block/"
            ).status_code,
            400,
        )

        self.assertEqual(
            self.client.post(
                f"/api/admin/users/{self.other_staff.pk}/block/"
            ).status_code,
            403,
        )

    def test_delete_member_but_not_staff(self):
        self.client.force_authenticate(self.admin)

        self.assertEqual(
            self.client.delete(
                f"/api/admin/users/{self.member.pk}/"
            ).status_code,
            204,
        )

        self.assertEqual(
            self.client.delete(
                f"/api/admin/users/{self.other_staff.pk}/"
            ).status_code,
            403,
        )


class EditUserInfoTests(APITestCase):
    """The administrator can correct a member's account and profile information."""

    def setUp(self):
        self.admin = User.objects.create_user(
            "boss", "boss@example.com", "pw12345!", is_staff=True
        )
        self.member = User.objects.create_user(
            "member", "m@example.com", "pw12345!"
        )

        UserProfile.objects.create(
            user=self.member,
            full_name="Old Name",
            location="Mirpur",
        )

        self.other = User.objects.create_user(
            "other", "o@example.com", "pw12345!"
        )

        self.client.force_authenticate(self.admin)
        self.url = f"/api/admin/users/{self.member.pk}/"

    def test_edit_account_and_profile(self):
        response = self.client.patch(
            self.url,
            {
                "username": "newname",
                "email": "new@example.com",
                "full_name": "New Name",
                "gender": "female",
                "location": "Dhanmondi",
                "bio": "Loves tong tea",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["username"], "newname")
        self.assertEqual(data["full_name"], "New Name")
        self.assertEqual(data["location"], "Dhanmondi")

        self.member.refresh_from_db()

        self.assertEqual(self.member.email, "new@example.com")
        self.assertEqual(
            self.member.profile.bio,
            "Loves tong tea",
        )
        self.assertEqual(
            self.member.profile.gender,
            "female",
        )

    def test_partial_edit_keeps_other_fields(self):
        self.client.patch(
            self.url,
            {"location": "Diyabari"},
            format="json",
        )

        self.member.refresh_from_db()

        self.assertEqual(
            self.member.profile.location,
            "Diyabari",
        )
        self.assertEqual(
            self.member.profile.full_name,
            "Old Name",
        )
        self.assertEqual(self.member.username, "member")

    def test_profile_is_created_when_missing(self):
        url = f"/api/admin/users/{self.other.pk}/"

        response = self.client.patch(
            url,
            {"full_name": "Other Person"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            UserProfile.objects.get(
                user=self.other
            ).full_name,
            "Other Person",
        )

    def test_duplicate_username_or_email_is_rejected(self):
        response = self.client.patch(
            self.url,
            {"username": "OTHER"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json())

        response = self.client.patch(
            self.url,
            {"email": "O@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

        self.member.refresh_from_db()
        self.assertEqual(self.member.username, "member")

    def test_own_username_and_email_can_be_resubmitted(self):
        response = self.client.patch(
            self.url,
            {
                "username": "member",
                "email": "m@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_invalid_values_are_rejected(self):
        self.assertEqual(
            self.client.patch(
                self.url,
                {"gender": "robot"},
                format="json",
            ).status_code,
            400,
        )

        self.assertEqual(
            self.client.patch(
                self.url,
                {"email": "not-an-email"},
                format="json",
            ).status_code,
            400,
        )

        self.assertEqual(
            self.client.patch(
                self.url,
                {"full_name": "   "},
                format="json",
            ).status_code,
            400,
        )

    def test_cannot_edit_self_or_staff(self):
        other_staff = User.objects.create_user(
            "staff2",
            "s2@example.com",
            "pw12345!",
            is_staff=True,
        )

        self.assertEqual(
            self.client.patch(
                f"/api/admin/users/{self.admin.pk}/",
                {"location": "X"},
                format="json",
            ).status_code,
            400,
        )

        self.assertEqual(
            self.client.patch(
                f"/api/admin/users/{other_staff.pk}/",
                {"location": "X"},
                format="json",
            ).status_code,
            403,
        )

    def test_normal_user_cannot_edit(self):
        self.client.force_authenticate(self.other)

        self.assertEqual(
            self.client.patch(
                self.url,
                {"location": "X"},
                format="json",
            ).status_code,
            403,
        )

    def test_edit_does_not_change_block_state_or_password(self):
        self.member.is_active = False
        self.member.save()

        old_hash = self.member.password

        self.client.patch(
            self.url,
            {"full_name": "Someone"},
            format="json",
        )

        self.member.refresh_from_db()

        self.assertFalse(self.member.is_active)
        self.assertEqual(self.member.password, old_hash)

    def test_list_shows_profile_info_and_searches_by_full_name(self):
        rows = self.client.get("/api/admin/users/").json()

        member_row = next(
            row for row in rows
            if row["username"] == "member"
        )

        self.assertEqual(member_row["full_name"], "Old Name")

        found = self.client.get(
            "/api/admin/users/?search=Old Name"
        ).json()

        self.assertEqual(
            [row["username"] for row in found],
            ["member"],
        )


class TransportAdministrationTests(APITestCase):
    def setUp(self):
        from transport.models import (
            FareStatus,
            FareSubmission,
            Location,
            LocationStatus,
            TransportMode,
        )

        self.FareStatus = FareStatus
        self.FareSubmission = FareSubmission
        self.Location = Location
        self.LocationStatus = LocationStatus
        self.TransportMode = TransportMode

        self.admin = User.objects.create_user(
            "transport-admin",
            "ta@example.com",
            "safe-test-password",
            is_staff=True,
        )

        self.member = User.objects.create_user(
            "transport-member",
            "tm@example.com",
            "safe-test-password",
        )

        self.origin = Location.objects.create(
            name="Farmgate",
            area="Tejgaon",
            latitude="23.757000",
            longitude="90.389000",
            status=LocationStatus.APPROVED,
        )

        self.destination = Location.objects.create(
            name="Shahbagh",
            area="Ramna",
            latitude="23.738000",
            longitude="90.395000",
            status=LocationStatus.APPROVED,
        )

        self.mode = TransportMode.objects.get(name="Bus")

        self.fare = FareSubmission.objects.create(
            origin=self.origin,
            destination=self.destination,
            transport_mode=self.mode,
            fare="25.00",
            submitted_by=self.member,
        )

        self.client.force_authenticate(self.admin)

    def test_location_admin_crud_and_staff_permission(self):
        response = self.client.get("/api/admin/locations/")
        self.assertEqual(response.status_code, 200)

        created = self.client.post(
            "/api/admin/locations/",
            {
                "name": "Motijheel",
                "area": "Motijheel",
                "description": "Central area",
                "latitude": 23.733,
                "longitude": 90.417,
            },
            format="json",
        )

        self.assertEqual(created.status_code, 201, created.data)

        location_id = created.data["id"]

        self.assertEqual(
            self.client.patch(
                f"/api/admin/locations/{location_id}/",
                {"area": "Dhaka"},
                format="json",
            ).status_code,
            200,
        )

        self.assertEqual(
            self.client.delete(
                f"/api/admin/locations/{location_id}/"
            ).status_code,
            204,
        )

        self.client.force_authenticate(self.member)

        self.assertEqual(
            self.client.get("/api/admin/locations/").status_code,
            403,
        )

    def test_location_referenced_by_fare_cannot_be_deleted(self):
        response = self.client.delete(
            f"/api/admin/locations/{self.origin.pk}/"
        )

        self.assertEqual(response.status_code, 409)

    def test_transport_mode_create_edit_activate_deactivate(self):
        created = self.client.post(
            "/api/admin/transport-modes/",
            {"name": "Electric shuttle"},
            format="json",
        )

        self.assertEqual(created.status_code, 201, created.data)

        mode_id = created.data["id"]

        self.assertEqual(
            self.client.post(
                f"/api/admin/transport-modes/{mode_id}/deactivate/"
            ).status_code,
            200,
        )

        self.assertFalse(
            self.TransportMode.objects.get(pk=mode_id).is_active
        )

        public_names = [
            item["name"]
            for item in self.client.get(
                "/api/transport/modes/"
            ).json()
        ]

        self.assertNotIn("Electric shuttle", public_names)

        self.assertEqual(
            self.client.post(
                f"/api/admin/transport-modes/{mode_id}/activate/"
            ).status_code,
            200,
        )

        self.assertTrue(
            self.TransportMode.objects.get(pk=mode_id).is_active
        )

        self.assertEqual(
            self.client.patch(
                f"/api/admin/transport-modes/{mode_id}/",
                {"name": "Shuttle"},
                format="json",
            ).status_code,
            200,
        )

        self.assertEqual(
            self.client.delete(
                f"/api/admin/transport-modes/{self.mode.pk}/"
            ).status_code,
            409,
        )

    def test_inactive_mode_cannot_be_used_for_new_fare(self):
        self.mode.is_active = False
        self.mode.save(update_fields=["is_active"])

        self.client.force_authenticate(self.member)

        response = self.client.post(
            "/api/transport/fares/",
            {
                "origin": self.origin.pk,
                "destination": self.destination.pk,
                "transport_mode": self.mode.pk,
                "fare": "30.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("transport_mode", response.data)

    def test_fare_moderation_and_public_listing(self):
        url = f"/api/admin/fares/{self.fare.pk}/approve/"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200, response.data)

        self.fare.refresh_from_db()

        self.assertEqual(
            self.fare.status,
            self.FareStatus.APPROVED,
        )

        public_rows = self.client.get(
            "/api/transport/fares/"
        ).json()

        self.assertEqual(
            [row["id"] for row in public_rows],
            [self.fare.pk],
        )

        self.assertEqual(
            self.client.get(
                "/api/admin/fares/?status=approved"
            ).status_code,
            200,
        )

        self.assertEqual(
            self.client.post(
                f"/api/admin/fares/{self.fare.pk}/reject/"
            ).status_code,
            200,
        )

        self.fare.refresh_from_db()

        self.assertEqual(
            self.fare.status,
            self.FareStatus.REJECTED,
        )

        self.assertEqual(
            self.client.get("/api/transport/fares/").json(),
            [],
        )

    def test_activity_log_records_moderation(self):
        self.client.post(
            f"/api/admin/fares/{self.fare.pk}/approve/"
        )

        response = self.client.get("/api/admin/activity/")

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            any(
                row["entity"] == "fare submission"
                and row["action"] == "approved"
                for row in response.json()
            )
        )

    def test_admin_stats_include_transport_counts(self):
        data = self.client.get("/api/admin/stats/").json()

        self.assertEqual(data["locations"], 2)
        self.assertGreaterEqual(data["transport_modes"], 4)
        self.assertEqual(data["pending_fares"], 1)


class LocationModerationTests(APITestCase):
    def setUp(self):
        from transport.models import Location, LocationStatus

        self.Location = Location
        self.LocationStatus = LocationStatus

        self.admin = User.objects.create_user(
            "location-admin",
            "la@example.com",
            "safe-test-password",
            is_staff=True,
        )

        self.member = User.objects.create_user(
            "location-member",
            "lm@example.com",
            "safe-test-password",
        )

    def test_user_submission_is_pending_and_hidden_publicly_until_approved(self):
        self.client.force_authenticate(self.member)

        response = self.client.post(
            "/api/transport/locations/",
            {
                "name": "New Market",
                "area": "Dhaka",
                "description": "Suggested stop",
                "latitude": 23.750000,
                "longitude": 90.390000,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

        location_id = response.data["id"]

        # The public serializer intentionally excludes the status field.
        # Verify the actual database record instead.
        submitted_location = self.Location.objects.get(
            pk=location_id
        )

        self.assertEqual(
            submitted_location.status,
            self.LocationStatus.PENDING,
        )

        self.assertEqual(
            self.client.get(
                "/api/transport/locations/"
            ).json(),
            [],
        )

        self.client.force_authenticate(self.admin)

        approved = self.client.post(
            f"/api/admin/locations/{location_id}/approve/"
        )

        self.assertEqual(approved.status_code, 200)

        public_ids = [
            row["id"]
            for row in self.client.get(
                "/api/transport/locations/"
            ).json()
        ]

        self.assertIn(location_id, public_ids)

    def test_admin_can_reject_location(self):
        location = self.Location.objects.create(
            name="Test stop",
            area="Dhaka",
            latitude="23.750000",
            longitude="90.390000",
            status=self.LocationStatus.PENDING,
        )

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f"/api/admin/locations/{location.pk}/reject/"
        )

        self.assertEqual(response.status_code, 200)

        location.refresh_from_db()

        self.assertEqual(
            location.status,
            self.LocationStatus.REJECTED,
        )
