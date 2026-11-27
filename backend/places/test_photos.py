from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase, APIClient

from administration.models import AdminActivityLog
from .models import Place, PlacePhoto


def picture(name="sample.png", image_format="PNG"):
    stream = BytesIO()
    Image.new("RGB", (8, 5), "green").save(stream, image_format)
    return SimpleUploadedFile(name, stream.getvalue(), content_type="application/octet-stream")


class PhotoWorkflowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.owner = users.create_user("photographer")
        cls.other = users.create_user("visitor")
        cls.staff = users.create_user("photo-moderator", is_staff=True)
        cls.place = Place.objects.create(name="Market", category="Shopping", area="Dhaka")
        cls.second = Place.objects.create(name="Park", category="Outdoors", area="Dhaka")

    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.media = Path(folder.name)
        self.enterContext(override_settings(MEDIA_ROOT=self.media))
        self.member, self.visitor, self.admin = APIClient(), APIClient(), APIClient()
        for client, user in [(self.member, self.owner), (self.visitor, self.other), (self.admin, self.staff)]:
            client.force_authenticate(user)
        self.path = f"/api/places/{self.place.pk}/photos/"

    def upload(self, client=None):
        response = (client or self.member).post(self.path, {"image": picture(), "caption": "Entrance",
            "place": self.second.pk, "user": self.other.pk, "status": "approved"}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_private_upload_to_public_display_and_removal(self):
        photo = self.upload()
        detail = self.path + str(photo["id"]) + "/"
        content = urlsplit(photo["image_url"]).path
        self.assertEqual((photo["place"], photo["user"], photo["status"]), (self.place.pk, self.owner.pk, "pending"))
        self.assertNotIn("image", photo)
        self.assertEqual(self.client.get(self.path).data, [])
        self.assertEqual(self.member.get(self.path).data[0]["username"], self.owner.username)
        self.assertEqual(self.client.get(content, HTTP_ACCEPT="image/jpeg").status_code, 404)
        self.assertEqual(self.visitor.get(detail).status_code, 404)
        self.assertEqual(self.member.get(detail.replace(f"/places/{self.place.pk}/", f"/places/{self.second.pk}/")).status_code, 404)
        self.assertEqual(self.admin.get("/api/admin/stats/").data["pending_photos"], 1)
        row = self.admin.get("/api/admin/photos/?status=pending").data[0]
        self.assertEqual((row["place_name"], row["caption"]), (self.place.name, "Entrance"))
        action = f"/api/admin/photos/{photo['id']}/"
        self.assertEqual(self.member.post(action + "approve/").status_code, 403)
        self.assertEqual(self.admin.post(action + "reject/", {"reason": " "}).status_code, 400)
        self.assertEqual(self.admin.post(action + "reject/", {"reason": "Image is unclear"}).status_code, 200)
        self.assertEqual(self.member.get(detail).data["rejection_reason"], "Image is unclear")
        self.assertEqual(self.visitor.get(content).status_code, 404)
        self.assertEqual(self.admin.post(action + "approve/").status_code, 200)
        self.assertEqual(self.client.get(self.path).data[0]["status"], "approved")
        self.assertFalse(self.visitor.get(detail).data["can_delete"])
        self.assertEqual(self.visitor.delete(detail).status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 401)
        data = self.client.get(content, HTTP_ACCEPT="image/jpeg")
        self.assertEqual((data.status_code, data["Content-Type"]), (200, "image/jpeg"))
        with Image.open(BytesIO(b"".join(data.streaming_content))) as saved:
            self.assertEqual((saved.format, saved.size), ("JPEG", (8, 5)))
        self.assertEqual(self.client.get(f"/api/places/{self.second.pk}/photos/").data, [])
        filename = PlacePhoto.objects.get(pk=photo["id"]).image.path
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.admin.delete(detail).status_code, 204)
        self.assertFalse(Path(filename).exists())
        self.assertEqual(self.client.get(content).status_code, 404)
        self.assertTrue(AdminActivityLog.objects.filter(entity="place photo", action="deleted", actor=self.staff).exists())

    def test_input_validation_and_missing_place(self):
        self.assertEqual(self.client.post(self.path, {"image": picture()}, format="multipart").status_code, 401)
        self.assertEqual(self.member.post(self.path, {"caption": "No file"}, format="multipart").status_code, 400)
        invalid = SimpleUploadedFile("sample.jpg", b"plain text", content_type="image/jpeg")
        self.assertEqual(self.member.post(self.path, {"image": invalid}, format="multipart").status_code, 400)
        with patch("places.photos.MAX_UPLOAD_BYTES", 12):
            self.assertEqual(self.member.post(self.path, {"image": picture()}, format="multipart").status_code, 400)
        with patch("places.photos.MAX_PIXELS", 10):
            self.assertEqual(self.member.post(self.path, {"image": picture()}, format="multipart").status_code, 400)
        self.assertEqual(self.member.post("/api/places/999999/photos/", {"image": picture()}, format="multipart").status_code, 404)
        self.assertFalse(PlacePhoto.objects.exists())
        self.assertFalse(any(self.media.rglob("*.jpg")))

    def test_owner_delete_cascade_and_rollback(self):
        photo = self.upload()
        file = Path(PlacePhoto.objects.get(pk=photo["id"]).image.path)
        with transaction.atomic():
            self.place.delete()
            transaction.set_rollback(True)
        self.assertTrue(file.exists())
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.member.delete(self.path + str(photo["id"]) + "/").status_code, 204)
        self.assertFalse(file.exists())
        another = self.upload()
        file = Path(PlacePhoto.objects.get(pk=another["id"]).image.path)
        with self.captureOnCommitCallbacks(execute=True):
            Place.objects.get(pk=another["place"]).delete()
        self.assertFalse(file.exists())

    def test_still_formats_and_storage_failures(self):
        for image_format in ("JPEG", "WEBP"):
            with self.subTest(image_format=image_format):
                response = self.member.post(self.path, {"image": picture(image_format=image_format)}, format="multipart")
                self.assertEqual(response.status_code, 201, response.data)
        gif = self.member.post(self.path, {"image": picture(image_format="GIF")}, format="multipart")
        self.assertEqual(gif.status_code, 400)
        before = set(self.media.rglob("*.jpg"))
        storage = PlacePhoto._meta.get_field("image").storage
        with patch.object(storage, "save", side_effect=OSError("unavailable")):
            result = self.member.post(self.path, {"image": picture()}, format="multipart")
        self.assertEqual(result.status_code, 503)
        self.assertEqual(PlacePhoto.objects.count(), 2)
        self.assertEqual(set(self.media.rglob("*.jpg")), before)

    def test_reversing_approval_also_restricts_the_existing_image_url(self):
        photo = self.upload()
        action = f"/api/admin/photos/{photo['id']}/"
        content = urlsplit(photo["image_url"]).path
        self.admin.post(action + "approve/")
        response = self.client.get(content)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        b"".join(response.streaming_content)
        self.admin.post(action + "reject/", {"reason": "Wrong location."})
        self.assertEqual(self.client.get(content).status_code, 404)
        self.assertEqual(self.member.get(self.path).data[0]["rejection_reason"], "Wrong location.")

    def test_staff_upload_requires_another_moderator(self):
        photo = self.upload(self.admin)
        self.assertEqual(self.admin.post(f"/api/admin/photos/{photo['id']}/approve/").status_code, 403)
        self.assertEqual(self.client.get(self.path).data, [])

    def test_missing_stored_file_has_an_http_error(self):
        photo = self.upload()
        Path(PlacePhoto.objects.get(pk=photo["id"]).image.path).unlink()
        response = self.member.get(urlsplit(photo["image_url"]).path, HTTP_ACCEPT="image/jpeg")
        self.assertEqual(response.status_code, 404)
