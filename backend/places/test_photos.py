
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

from .models import ItemStatus, Place, PlacePhoto

User = get_user_model()


def make_test_image(name="place-photo.jpg", image_format="JPEG"):
    output = BytesIO()
    Image.new("RGB", (12, 12), color=(80, 120, 160)).save(
        output,
        format=image_format,
    )
    content_type = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }[image_format]

    return SimpleUploadedFile(
        name,
        output.getvalue(),
        content_type=content_type,
    )


def close_file_response(response):
    closers = list(getattr(response, "_resource_closers", []))

    for closer in closers:
        closer()

    response._resource_closers = []

    file_handle = getattr(response, "file_to_stream", None)
    if file_handle is not None and not getattr(file_handle, "closed", False):
        file_handle.close()


class PlacePhotoSubmissionTests(APITestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.user = User.objects.create_user(
            username="photo_user",
            password="test-password-123",
        )
        self.other_user = User.objects.create_user(
            username="another_photo_user",
            password="test-password-456",
        )
        self.place = Place.objects.create(
            name="Test Cafe",
            category="Cafe",
            area="Dhanmondi",
        )
        self.url = reverse(
            "place-photo-list-create",
            args=[self.place.pk],
        )

    def test_authenticated_user_can_upload_photo_for_place(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "image_upload": make_test_image(),
                "caption": "Front seating area",
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        photo = PlacePhoto.objects.get(pk=response.data["id"])
        self.assertEqual(photo.place, self.place)
        self.assertEqual(photo.submitted_by, self.user)
        self.assertEqual(photo.status, ItemStatus.PENDING)
        self.assertEqual(photo.caption, "Front seating area")

    def test_anonymous_user_cannot_upload_photo(self):
        response = self.client.post(
            self.url,
            {"image_upload": make_test_image()},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(PlacePhoto.objects.count(), 0)

    def test_public_list_only_returns_approved_photos(self):
        pending = PlacePhoto.objects.create(
            place=self.place,
            submitted_by=self.user,
            image=make_test_image("pending.jpg"),
            status=ItemStatus.PENDING,
        )

        approved = PlacePhoto.objects.create(
            place=self.place,
            submitted_by=self.other_user,
            image=make_test_image("approved.jpg"),
            status=ItemStatus.APPROVED,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [row["id"] for row in response.data],
            [approved.pk],
        )
        self.assertNotIn(
            pending.pk,
            [row["id"] for row in response.data],
        )

    def test_pending_photo_file_is_private_to_owner_and_staff(self):
        photo = PlacePhoto.objects.create(
            place=self.place,
            submitted_by=self.user,
            image=make_test_image("private-pending.jpg"),
            status=ItemStatus.PENDING,
        )

        image_url = reverse(
            "place-photo-image",
            args=[photo.pk],
        )

        anonymous_response = self.client.get(image_url)
        self.assertEqual(
            anonymous_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(self.other_user)
        other_user_response = self.client.get(image_url)
        self.assertEqual(
            other_user_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(self.user)
        owner_response = self.client.get(image_url)
        self.addCleanup(close_file_response, owner_response)

        self.assertEqual(
            owner_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            owner_response["Content-Type"],
            "image/jpeg",
        )

    def test_approved_photo_file_is_public(self):
        photo = PlacePhoto.objects.create(
            place=self.place,
            submitted_by=self.user,
            image=make_test_image("public-approved.jpg"),
            status=ItemStatus.APPROVED,
        )

        response = self.client.get(
            reverse("place-photo-image", args=[photo.pk])
        )
        self.addCleanup(close_file_response, response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_user_can_only_see_their_own_photo_submissions(self):
        own_photo = PlacePhoto.objects.create(
            place=self.place,
            submitted_by=self.user,
            image=make_test_image("own.jpg"),
        )

        other_photo = PlacePhoto.objects.create(
            place=self.place,
            submitted_by=self.other_user,
            image=make_test_image("other.jpg"),
        )

        self.client.force_authenticate(self.user)

        response = self.client.get(
            reverse("my-place-photos", args=[self.place.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [row["id"] for row in response.data],
            [own_photo.pk],
        )
        self.assertNotIn(
            other_photo.pk,
            [row["id"] for row in response.data],
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

    def test_non_image_upload_is_rejected(self):
        self.client.force_authenticate(self.user)

        invalid_file = SimpleUploadedFile(
            "not-an-image.jpg",
            b"this is not an image",
            content_type="image/jpeg",
        )

        response = self.client.post(
            self.url,
            {"image_upload": invalid_file},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(PlacePhoto.objects.count(), 0)

    def test_image_extension_must_match_actual_format(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "image_upload": make_test_image(
                    "wrong-extension.png",
                    "JPEG",
                )
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(PlacePhoto.objects.count(), 0)

    def test_upload_larger_than_five_megabytes_is_rejected(self):
        self.client.force_authenticate(self.user)

        large_file = SimpleUploadedFile(
            "large-photo.jpg",
            b"x" * (5 * 1024 * 1024 + 1),
            content_type="image/jpeg",
        )

        response = self.client.post(
            self.url,
            {"image_upload": large_file},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(PlacePhoto.objects.count(), 0)
