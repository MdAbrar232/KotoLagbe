from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from rest_framework.test import APITestCase

User = get_user_model()


class AdministrationApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("boss", "boss@example.com", "pw12345!", is_staff=True)
        self.member = User.objects.create_user("member", "m@example.com", "pw12345!")
        self.other_staff = User.objects.create_user("staff2", "s2@example.com", "pw12345!", is_staff=True)

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.get("/api/admin/stats/").status_code, (401, 403))

    def test_normal_user_is_rejected(self):
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get("/api/admin/places/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/users/").status_code, 403)

    def test_staff_can_open_dashboard_and_lists(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/admin/stats/").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/places/").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/users/").status_code, 200)

    def test_block_and_unblock_member(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f"/api/admin/users/{self.member.pk}/block/").status_code, 200)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.client.post(f"/api/admin/users/{self.member.pk}/unblock/")
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)

    def test_cannot_block_self_or_other_staff(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f"/api/admin/users/{self.admin.pk}/block/").status_code, 400)
        self.assertEqual(self.client.post(f"/api/admin/users/{self.other_staff.pk}/block/").status_code, 403)

    def test_delete_member_but_not_staff(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f"/api/admin/users/{self.member.pk}/").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/admin/users/{self.other_staff.pk}/").status_code, 403)


class EditUserInfoTests(APITestCase):
    """The administrator can correct a member's account and profile information."""

    def setUp(self):
        self.admin = User.objects.create_user("boss", "boss@example.com", "pw12345!", is_staff=True)
        self.member = User.objects.create_user("member", "m@example.com", "pw12345!")
        UserProfile.objects.create(user=self.member, full_name="Old Name", location="Mirpur")
        self.other = User.objects.create_user("other", "o@example.com", "pw12345!")
        self.client.force_authenticate(self.admin)
        self.url = f"/api/admin/users/{self.member.pk}/"

    def test_edit_account_and_profile(self):
        response = self.client.patch(self.url, {
            "username": "newname", "email": "new@example.com", "full_name": "New Name",
            "gender": "female", "location": "Dhanmondi", "bio": "Loves tong tea",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "newname")
        self.assertEqual(data["full_name"], "New Name")
        self.assertEqual(data["location"], "Dhanmondi")
        self.member.refresh_from_db()
        self.assertEqual(self.member.email, "new@example.com")
        self.assertEqual(self.member.profile.bio, "Loves tong tea")
        self.assertEqual(self.member.profile.gender, "female")

    def test_partial_edit_keeps_other_fields(self):
        self.client.patch(self.url, {"location": "Diyabari"}, format="json")
        self.member.refresh_from_db()
        self.assertEqual(self.member.profile.location, "Diyabari")
        self.assertEqual(self.member.profile.full_name, "Old Name")
        self.assertEqual(self.member.username, "member")

    def test_profile_is_created_when_missing(self):
        url = f"/api/admin/users/{self.other.pk}/"
        response = self.client.patch(url, {"full_name": "Other Person"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserProfile.objects.get(user=self.other).full_name, "Other Person")

    def test_duplicate_username_or_email_is_rejected(self):
        response = self.client.patch(self.url, {"username": "OTHER"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json())
        response = self.client.patch(self.url, {"email": "O@example.com"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.member.refresh_from_db()
        self.assertEqual(self.member.username, "member")

    def test_own_username_and_email_can_be_resubmitted(self):
        response = self.client.patch(self.url, {"username": "member", "email": "m@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_invalid_values_are_rejected(self):
        self.assertEqual(self.client.patch(self.url, {"gender": "robot"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url, {"email": "not-an-email"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url, {"full_name": "   "}, format="json").status_code, 400)

    def test_cannot_edit_self_or_staff(self):
        other_staff = User.objects.create_user("staff2", "s2@example.com", "pw12345!", is_staff=True)
        self.assertEqual(self.client.patch(f"/api/admin/users/{self.admin.pk}/", {"location": "X"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/admin/users/{other_staff.pk}/", {"location": "X"}, format="json").status_code, 403)

    def test_normal_user_cannot_edit(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.patch(self.url, {"location": "X"}, format="json").status_code, 403)

    def test_edit_does_not_change_block_state_or_password(self):
        self.member.is_active = False
        self.member.save()
        old_hash = self.member.password
        self.client.patch(self.url, {"full_name": "Someone"}, format="json")
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertEqual(self.member.password, old_hash)

    def test_list_shows_profile_info_and_searches_by_full_name(self):
        rows = self.client.get("/api/admin/users/").json()
        member_row = next(r for r in rows if r["username"] == "member")
        self.assertEqual(member_row["full_name"], "Old Name")
        found = self.client.get("/api/admin/users/?search=Old Name").json()
        self.assertEqual([r["username"] for r in found], ["member"])
