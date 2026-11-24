
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from places.models import (
    Place,
    PlaceItem,
    ItemPriceSubmission,
    ItemStatus,
)


User = get_user_model()


class ItemModerationTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="item-admin",
            password="testpassword123",
            is_staff=True,
        )

        self.member = User.objects.create_user(
            username="item-member",
            password="testpassword123",
        )

        self.place = Place.objects.create(
            name="Test Restaurant",
            category="Restaurant",
            area="Dhaka",
        )

        self.item = PlaceItem.objects.create(
            place=self.place,
            name="Chicken Burger",
            category="Food",
            submitted_by=self.member,
            status=ItemStatus.PENDING,
        )

        self.price = ItemPriceSubmission.objects.create(
            item=self.item,
            submitted_by=self.member,
            price="250.00",
            status=ItemStatus.PENDING,
        )

        self.client.force_authenticate(user=self.admin)

    def test_admin_can_approve_item(self):
        response = self.client.post(
            f"/api/admin/items/{self.item.pk}/approve/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ItemStatus.APPROVED)
        self.assertEqual(self.item.reviewed_by, self.admin)

    def test_admin_must_provide_rejection_reason(self):
        response = self.client.post(
            f"/api/admin/items/{self.item.pk}/reject/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_can_reject_item_with_reason(self):
        response = self.client.post(
            f"/api/admin/items/{self.item.pk}/reject/",
            {"reason": "Duplicate item"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ItemStatus.REJECTED)
        self.assertEqual(
            self.item.rejection_reason,
            "Duplicate item",
        )

    def test_contributor_cannot_moderate_own_item(self):
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            f"/api/admin/items/{self.item.pk}/approve/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_price_cannot_be_approved_before_item(self):
        response = self.client.post(
            f"/api/admin/item-prices/{self.price.pk}/approve/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_can_approve_price_after_item(self):
        self.item.status = ItemStatus.APPROVED
        self.item.save(update_fields=["status"])

        response = self.client.post(
            f"/api/admin/item-prices/{self.price.pk}/approve/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.price.refresh_from_db()
        self.assertEqual(self.price.status, ItemStatus.APPROVED)
        self.assertEqual(self.price.reviewed_by, self.admin)

    def test_admin_can_list_pending_items(self):
        response = self.client.get(
            "/api/admin/items/?status=pending"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_list_pending_prices(self):
        response = self.client.get(
            "/api/admin/item-prices/?status=pending"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderation_creates_activity_log(self):
        response = self.client.post(
            f"/api/admin/items/{self.item.pk}/approve/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        from administration.models import AdminActivityLog

        self.assertTrue(
            AdminActivityLog.objects.filter(
                actor=self.admin,
                entity="place item",
                entity_id=str(self.item.pk),
                action=ItemStatus.APPROVED,
            ).exists()
        )
