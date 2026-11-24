from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Place, PlaceReview, ItemStatus


class PlaceReviewTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.user = User.objects.create_user(
            username="reviewer",
            password="test-password-123",
        )

        cls.other_user = User.objects.create_user(
            username="other_reviewer",
            password="test-password-456",
        )

        cls.place = Place.objects.create(
            name="Test Restaurant",
            category="restaurant",
            area="Dhanmondi",
            address="Test address",
            description="Test place",
        )

    def list_url(self):
        return reverse(
            "place-review-list-create",
            args=[self.place.pk],
        )

    def detail_url(self, review):
        return reverse(
            "place-review-detail",
            args=[self.place.pk, review.pk],
        )

    def create_review(self, user=None, rating=4, review_status=ItemStatus.APPROVED):
        return PlaceReview.objects.create(
            place=self.place,
            user=user or self.user,
            rating=rating,
            comment="A test review",
            status=review_status,
        )

    def test_anonymous_user_can_view_approved_reviews(self):
        review = self.create_review()

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], review.pk)

    def test_anonymous_user_cannot_submit_review(self):
        response = self.client.post(
            self.list_url(),
            {"rating": 5, "comment": "Excellent"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_submit_pending_review(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.list_url(),
            {"rating": 5, "comment": "Excellent place"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.assertEqual(response.data["status"], ItemStatus.PENDING)
        self.assertEqual(response.data["rating"], 5)
        self.assertEqual(response.data["user"], self.user.pk)

    def test_user_cannot_review_same_place_twice(self):
        self.create_review(review_status=ItemStatus.PENDING)
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.list_url(),
            {"rating": 3, "comment": "Another review"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_pending_and_rejected_reviews_are_not_public(self):
        self.create_review(review_status=ItemStatus.PENDING)

        self.create_review(
            user=self.other_user,
            rating=2,
            review_status=ItemStatus.REJECTED,
        )

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_owner_can_edit_review_and_it_returns_to_pending(self):
        review = self.create_review()

        self.client.force_authenticate(self.user)

        response = self.client.patch(
            self.detail_url(review),
            {"rating": 3, "comment": "Changed my opinion"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ItemStatus.PENDING)
        self.assertEqual(response.data["rating"], 3)

        review.refresh_from_db()
        self.assertEqual(review.reviewed_by, None)
        self.assertEqual(review.rejection_reason, "")

    def test_another_user_cannot_edit_or_delete_review(self):
        review = self.create_review()

        self.client.force_authenticate(self.other_user)

        edit_response = self.client.patch(
            self.detail_url(review),
            {"rating": 1},
            format="json",
        )

        delete_response = self.client.delete(
            self.detail_url(review),
        )

        self.assertEqual(
            edit_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            delete_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_owner_can_delete_review(self):
        review = self.create_review()

        self.client.force_authenticate(self.user)

        response = self.client.delete(self.detail_url(review))

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            PlaceReview.objects.filter(pk=review.pk).exists()
        )

    def test_place_rating_uses_approved_reviews_only(self):
        self.create_review(rating=5)

        self.create_review(
            user=self.other_user,
            rating=3,
        )

        pending_user = get_user_model().objects.create_user(
            username="pending_reviewer",
            password="test-password-789",
        )

        self.create_review(
            user=pending_user,
            rating=1,
            review_status=ItemStatus.PENDING,
        )

        response = self.client.get(
            reverse("place-detail", args=[self.place.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["average_rating"], "4.00")
        self.assertEqual(response.data["review_count"], 2)

    def test_rating_must_be_between_one_and_five(self):
        self.client.force_authenticate(self.user)

        for rating in (0, 6):
            with self.subTest(rating=rating):
                response = self.client.post(
                    self.list_url(),
                    {"rating": rating, "comment": "Invalid rating"},
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )