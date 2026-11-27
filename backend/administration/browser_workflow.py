"""Opt-in browser integration test. See ADMIN_MODULE_README.md for the build command."""
import os
import re
import secrets
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.test import LiveServerTestCase, override_settings
from django.urls import path, re_path
from django.views.static import serve
from PIL import Image
from playwright.sync_api import expect, sync_playwright

from config.urls import urlpatterns as app_urls
from places.models import Place
from transport.models import Location


DIST = Path(os.getenv("KOTOLAGBE_TEST_DIST", settings.BASE_DIR.parent / "frontend" / "dist"))


def index(request):
    return FileResponse((DIST / "index.html").open("rb"), content_type="text/html")


urlpatterns = [*app_urls, path("", index),
               re_path(r"^(?P<path>assets/.+|favicon\.svg)$", serve, {"document_root": DIST})]


@override_settings(ROOT_URLCONF=__name__)
class ModerationBrowserTest(LiveServerTestCase):
    def setUp(self):
        if not (DIST / "index.html").is_file():
            self.fail("Build the frontend with VITE_API_BASE_URL=/api before running the browser test.")
        media = self.enterContext(TemporaryDirectory())
        self.enterContext(override_settings(MEDIA_ROOT=media))
        self.password = secrets.token_urlsafe(18)
        users = get_user_model().objects
        users.create_user("member", password=self.password)
        users.create_user("moderator", password=self.password, is_staff=True)
        Place.objects.create(name="Test café", area="Dhaka", category="Cafe")
        Location.objects.create(name="Campus gate", area="Dhaka", latitude=23.75, longitude=90.4, status="approved")
        playwright = self.enterContext(sync_playwright())
        self.browser = playwright.chromium.launch(executable_path=os.environ.get("KOTOLAGBE_TEST_CHROMIUM"))
        self.addCleanup(self.browser.close)
        self.errors = []

    def page(self, username=None):
        page = self.browser.new_page()
        page.on("pageerror", lambda error: self.errors.append(str(error)))
        # Tile rendering uses a third-party server. The application and its API are live.
        page.route(re.compile(r"^https://[^/]*\.tile\.openstreetmap\.org/"), lambda route: route.abort())
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(self.live_server_url)
        if username:
            page.get_by_role("button", name="Sign in", exact=True).click()
            page.get_by_placeholder("Enter your username").fill(username)
            page.get_by_placeholder("Enter your password").fill(self.password)
            page.locator("button[type=submit]").click()
            expect(page.get_by_text("Hi, " + username, exact=True)).to_be_visible()
        return page

    def open_place(self, page):
        page.locator("button.brand-button").click()
        page.get_by_role("heading", name="Test café", exact=True).click()
        expect(page.get_by_role("heading", name="Items and prices")).to_be_visible()

    def queue(self, admin, section, text):
        admin.get_by_role("button", name=section, exact=True).click()
        admin.get_by_label("Filter by status").select_option("pending")
        row = admin.locator("tbody tr").filter(has_text=text)
        expect(row).to_be_visible()
        return row

    def approve(self, admin, section, text):
        row = self.queue(admin, section, text)
        row.get_by_role("button", name="Approve", exact=True).click()
        expect(row).to_have_count(0)

    def test_contributor_moderator_and_guest(self):
        member, admin, guest = self.page("member"), self.page("moderator"), self.page()
        expect(member.get_by_role("button", name="Admin Panel")).to_have_count(0)
        admin.get_by_role("button", name="Admin Panel").click()
        self.open_place(member)
        member.locator("summary").filter(has_text="Suggest an item").click()
        form = member.locator("form").filter(has=member.get_by_role("button", name="Submit item", exact=True))
        form.get_by_label("Item name").fill("Mint tea")
        form.get_by_label("Item category").fill("Drink")
        form.get_by_label("Price (BDT)").fill("25")
        form.get_by_role("button", name="Submit item").click()
        expect(member.get_by_text("Item and starting price submitted for staff review.")).to_be_visible()
        member.get_by_label("Your comment").fill("Quiet at noon.")
        member.get_by_role("button", name="Submit review").click()
        expect(member.get_by_text("Your review has been submitted for moderation.")).to_be_visible()
        image = BytesIO()
        Image.new("RGB", (20, 15), "green").save(image, "PNG")
        member.locator("input[type=file]").set_input_files(
            {"name": "entry.png", "mimeType": "image/png", "buffer": image.getvalue()})
        member.get_by_label("Caption (optional)").fill("Café entrance")
        member.get_by_role("button", name="Upload photo").click()
        expect(member.get_by_text("Photo submitted for staff review.")).to_be_visible()
        self.open_place(guest)
        expect(guest.get_by_text("No photos yet.")).to_be_visible()
        expect(guest.get_by_text("No approved items yet.")).to_be_visible()

        price = self.queue(admin, "Item prices", "Mint tea")
        expect(price.get_by_role("button", name="Approve")).to_be_disabled()
        self.approve(admin, "Place items", "Mint tea")
        self.approve(admin, "Item prices", "Mint tea")
        self.queue(admin, "Reviews", "Quiet at noon.").get_by_role("button", name="Reject").click()
        dialog = admin.get_by_role("dialog", name="Reject submission")
        expect(dialog.get_by_role("button", name="Confirm rejection")).to_be_disabled()
        dialog.get_by_label("Rejection reason").fill("Please give the day.")
        dialog.get_by_role("button", name="Confirm rejection").click()
        expect(dialog).to_have_count(0)
        self.open_place(member)
        expect(member.get_by_text("Reason: Please give the day.")).to_be_visible()
        member.get_by_label("Your comment").fill("Quiet on Friday.")
        member.get_by_role("button", name="Update review").click()
        expect(member.get_by_text("Your review has been updated and sent for moderation.")).to_be_visible()
        admin.get_by_role("button", name="Refresh list").click()
        self.approve(admin, "Reviews", "Quiet on Friday.")
        self.queue(admin, "Photos", "Café entrance")
        admin.wait_for_function("document.querySelector('img[alt=\"Café entrance\"]')?.naturalWidth > 0")
        self.approve(admin, "Photos", "Café entrance")
        self.open_place(guest)
        expect(guest.get_by_text("Quiet on Friday.")).to_be_visible()
        expect(guest.get_by_text("Average price: ৳25.00")).to_be_visible()
        guest.wait_for_function("document.querySelector('img[alt=\"Café entrance\"]')?.naturalWidth > 0")
        self.open_place(member)
        member.get_by_role("button", name="Delete photo").click()
        expect(member.get_by_text("Photo deleted.")).to_be_visible()
        self.open_place(guest)
        expect(guest.get_by_text("No photos yet.")).to_be_visible()
        self.assertEqual(self.errors, [])
