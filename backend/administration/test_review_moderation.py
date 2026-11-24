from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from administration.models import AdminActivityLog
from places.models import Place, PlaceReview, ItemStatus


class PlaceReviewModerationTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.admin = User.objects.create_user(
            username="review_admin",
            password="admin-password-123",
            is_staff=True,
        )

        cls.member = User.objects.create_user(
            username="review_member",
            password="member-password-123",
        )

        cls.place = Place.objects.create(
            name="Moderation Test Place",
            category="restaurant",
            area="Dhanmondi",
            address="Test address",
        )

        cls.review = PlaceReview.objects.create(
            place=cls.place,
            user=cls.member,
            rating=4,
            comment="Good place",
            status=ItemStatus.PENDING,
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_admin_can_list_pending_reviews(self):
        response = self.client.get(
            reverse("admin-reviews-list"),
            {"status": "pending"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_admin_can_approve_review(self):
        response = self.client.post(
            reverse(
                "admin-reviews-approve",
                args=[self.review.pk],
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.review.refresh_from_db()

        self.assertEqual(self.review.status, ItemStatus.APPROVED)
        self.assertEqual(self.review.reviewed_by, self.admin)
        self.assertIsNotNone(self.review.reviewed_at)

    def test_admin_must_provide_rejection_reason(self):
        response = self.client.post(
            reverse(
                "admin-reviews-reject",
                args=[self.review.pk],
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_can_reject_review_with_reason(self):
        response = self.client.post(
            reverse(
                "admin-reviews-reject",
                args=[self.review.pk],
            ),
            {"reason": "Inappropriate content"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.review.refresh_from_db()

        self.assertEqual(self.review.status, ItemStatus.REJECTED)
        self.assertEqual(
            self.review.rejection_reason,
            "Inappropriate content",
        )

    def test_moderation_creates_activity_log(self):
        self.client.post(
            reverse(
                "admin-reviews-approve",
                args=[self.review.pk],
            ),
        )

        self.assertTrue(
            AdminActivityLog.objects.filter(
                entity="place review",
                entity_id=str(self.review.pk),
                actor=self.admin,
            ).exists()
        )

    def test_non_admin_cannot_moderate_reviews(self):
        self.client.force_authenticate(self.member)

        response = self.client.post(
            reverse(
                "admin-reviews-approve",
                args=[self.review.pk],
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )