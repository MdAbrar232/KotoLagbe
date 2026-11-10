from django.contrib.auth import get_user_model
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
