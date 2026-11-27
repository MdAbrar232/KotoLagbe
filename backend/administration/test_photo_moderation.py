
from io import BytesIO
import tempfile
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from places.models import ItemStatus, Place, PlacePhoto

User = get_user_model()


def make_test_image(name="admin-photo.jpg"):
    output = BytesIO()
    Image.new("RGB", (12, 12), color=(120, 90, 60)).save(
        output,
        format="JPEG",
    )

    return SimpleUploadedFile(
        name,
        output.getvalue(),
        content_type="image/jpeg",
    )


def close_file_response(response):
    closers = list(getattr(response, "_resource_closers", []))

    for closer in closers:
        closer()

    response._resource_closers = []

    file_handle = getattr(response, "file_to_stream", None)
    if file_handle is not None and not getattr(file_handle, "closed", False):
        file_handle.close()


class PlacePhotoModerationTests(APITestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.contributor = User.objects.create_user(
            username="photo_contributor",
            password="test-password-123",
        )

        self.admin = User.objects.create_user(
            username="photo_admin",
            password="test-password-456",
            is_staff=True,
        )

        self.place = Place.objects.create(
            name="Moderation Cafe",
            category="Cafe",
            area="Uttara",
        )

        self.photo = PlacePhoto.objects.create(
            place=self.place,
            submitted_by=self.contributor,
            image=make_test_image(),
            status=ItemStatus.PENDING,
        )

        self.list_url = reverse("admin-photos-list")

    def test_only_staff_can_list_photo_submissions(self):
        response = self.client.get(self.list_url)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.client.force_authenticate(self.contributor)
        response = self.client.get(self.list_url)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], self.photo.pk)

        self.assertIn(
            f"/api/places/photos/{self.photo.pk}/image/",
            response.data[0]["image"],
        )

        signed_image = urlsplit(response.data[0]["image"])
        self.client.force_authenticate(user=None)

        image_response = self.client.get(
            f"{signed_image.path}?{signed_image.query}"
        )
        self.addCleanup(close_file_response, image_response)

        self.assertEqual(
            image_response.status_code,
            status.HTTP_200_OK,
        )

    def test_staff_can_view_pending_photo_file(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            reverse("place-photo-image", args=[self.photo.pk])
        )
        self.addCleanup(close_file_response, response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_approval_makes_photo_public_and_records_reviewer(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("admin-photos-approve", args=[self.photo.pk]),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.photo.refresh_from_db()

        self.assertEqual(self.photo.status, ItemStatus.APPROVED)
        self.assertEqual(self.photo.reviewed_by, self.admin)
        self.assertIsNotNone(self.photo.reviewed_at)

        public_response = self.client.get(
            reverse("place-photo-list-create", args=[self.place.pk])
        )

        self.assertEqual(
            public_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            [row["id"] for row in public_response.data],
            [self.photo.pk],
        )

    def test_rejection_requires_reason(self):
        self.client.force_authenticate(self.admin)

        url = reverse(
            "admin-photos-reject",
            args=[self.photo.pk],
        )

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        response = self.client.post(
            url,
            {"reason": "The photo is too blurry."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.photo.refresh_from_db()

        self.assertEqual(self.photo.status, ItemStatus.REJECTED)
        self.assertEqual(
            self.photo.rejection_reason,
            "The photo is too blurry.",
        )

    def test_admin_cannot_moderate_their_own_photo(self):
        own_photo = PlacePhoto.objects.create(
            place=self.place,
            submitted_by=self.admin,
            image=make_test_image("admin-own.jpg"),
            status=ItemStatus.PENDING,
        )

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse("admin-photos-approve", args=[own_photo.pk]),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
