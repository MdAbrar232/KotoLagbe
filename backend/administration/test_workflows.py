from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import AccessToken

from places.models import Place
from transport.models import Location, TransportMode


class AdministrationWorkflowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.owner = users.create_user("contributor")
        cls.other = users.create_user("second-member")
        cls.staff = users.create_user("moderator", is_staff=True)
        cls.stop = Location.objects.create(name="Gulshan", area="Dhaka", status="approved",
                                           latitude=23.79, longitude=90.41)
        cls.mode, _ = TransportMode.objects.get_or_create(name="Test bus")
        cls.place = Place.objects.create(name="Campus café", area="Dhaka", category="Food", location=cls.stop)

    def as_user(self, user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer " + str(AccessToken.for_user(user)))
        return client

    def setUp(self):
        self.member = self.as_user(self.owner)
        self.admin = self.as_user(self.staff)

    def post(self, client, path, data=None, expected=200):
        response = client.post(path, data or {}, format="json")
        self.assertEqual(response.status_code, expected, getattr(response, "data", None))
        return response.data

    def test_admin_root_lists_actions_and_blocked_tokens(self):
        for path in ("", "stats/", "places/", "users/", "locations/", "transport-modes/", "fares/",
                     "items/", "item-prices/", "reviews/", "photos/", "activity/"):
            with self.subTest(path=path):
                url = "/api/admin/" + path
                self.assertEqual(self.client.get(url).status_code, 401)
                self.assertEqual(self.member.get(url).status_code, 403)
                self.assertEqual(self.admin.get(url).status_code, 200)
        self.post(self.member, "/api/admin/items/1/approve/", expected=403)
        self.post(self.admin, f"/api/admin/users/{self.owner.pk}/block/")
        self.assertEqual(self.member.get("/api/accounts/profile/").status_code, 401)
        self.post(self.admin, f"/api/admin/users/{self.owner.pk}/unblock/")
        self.assertEqual(self.member.get("/api/accounts/profile/").status_code, 200)
        self.staff.is_active = False
        self.staff.save(update_fields=["is_active"])
        self.assertEqual(self.admin.get("/api/admin/stats/").status_code, 401)

    def test_place_administration_reuses_validated_relationships(self):
        path = "/api/admin/places/"
        data = {"name": "Coffee counter", "category": "Food", "area": "Dhaka",
                "parent": self.place.pk, "location": self.stop.pk}
        self.post(self.member, "/api/places/", data, 403)
        self.post(self.client, "/api/places/", data, 401)
        child = self.post(self.admin, path, data, 201)
        public = self.client.get(f"/api/places/{child['id']}/").data
        self.assertEqual((public["location_name"], public["parent_name"]), (self.stop.name, self.place.name))
        cycle = self.admin.patch(f"{path}{self.place.pk}/", {"parent": child["id"]}, format="json")
        self.assertEqual(cycle.status_code, 400)
        self.assertIn("parent", cycle.data)
        self.assertEqual(self.admin.delete(f"{path}{child['id']}/").status_code, 204)

    def test_rejected_location_disappears_from_public_place_links(self):
        path = f"/api/admin/locations/{self.stop.pk}/"
        self.post(self.admin, path + "reject/")
        details = self.client.get(f"/api/places/{self.place.pk}/").data
        self.assertIsNone(details["location"])
        self.assertIsNone(details["location_name"])
        self.assertEqual(self.client.get("/api/places/", {"location": self.stop.pk}).data, [])
        stored = self.admin.get(f"/api/admin/places/{self.place.pk}/").data
        self.assertEqual(stored["location"], self.stop.pk)
        self.post(self.admin, path + "approve/")
        self.assertEqual(self.client.get(f"/api/places/{self.place.pk}/").data["location"], self.stop.pk)

    def test_location_to_fare_and_route_summary(self):
        member_stop = self.post(self.member, "/api/transport/locations/",
                                {"name": "Library", "area": "Dhaka", "latitude": "23.75",
                                 "longitude": "90.38", "submitted_by": self.other.pk}, 201)
        stop_id = member_stop["id"]
        queue = self.admin.get("/api/admin/locations/", {"status": "pending"}).data
        self.assertEqual([(r["id"], r["contributor"]) for r in queue], [(stop_id, self.owner.username)])
        self.assertNotIn(stop_id, [r["id"] for r in self.client.get("/api/transport/locations/").data])
        location_action = f"/api/admin/locations/{stop_id}/"
        self.post(self.admin, location_action + "reject/")
        self.assertEqual(self.member.get("/api/accounts/submissions/").data[0]["status"], "rejected")
        self.post(self.admin, location_action + "approve/")
        fare = self.post(self.member, "/api/transport/fares/", {"origin": stop_id, "destination": self.stop.pk,
                         "transport_mode": self.mode.pk, "fare": "32.50", "submitted_by": self.other.pk}, 201)
        queue = self.admin.get("/api/admin/fares/?status=pending").data
        self.assertEqual((queue[0]["contributor"], queue[0]["origin_name"], queue[0]["fare"]),
                         (self.owner.username, "Library", "32.50"))
        self.assertEqual(self.client.get("/api/transport/fares/").data, [])
        action = f"/api/admin/fares/{fare['id']}/"
        self.post(self.admin, action + "reject/")
        self.assertEqual(self.client.get("/api/transport/fares/").data, [])
        self.post(self.admin, location_action + "reject/")
        self.post(self.admin, action + "approve/", expected=400)
        self.post(self.admin, location_action + "approve/")
        self.post(self.admin, action + "approve/")
        rows = self.client.get("/api/transport/fares/", {"origin": stop_id, "destination": self.stop.pk}).data
        self.assertEqual([(r["id"], r["submitted_by"]) for r in rows], [(fare["id"], self.owner.pk)])
        summary = self.client.get("/api/transport/fares/summary/", {"origin": stop_id, "destination": self.stop.pk}).data
        self.assertEqual(summary["transport_options"][0]["average_fare"], "32.50")
        self.assertEqual({r["type"] for r in self.member.get("/api/accounts/submissions/").data}, {"location", "fare"})

    def test_item_and_prices_keep_separate_approval_and_contributors(self):
        item = self.post(self.member, "/api/places/items/suggest/", {"place": self.place.pk, "name": "Tea",
                         "category": "Drink", "price": "25.00", "submitted_by": self.other.pk}, 201)
        self.assertEqual(item["status"], "pending")
        pending = self.admin.get("/api/admin/items/?status=pending").data[0]
        self.assertEqual((pending["id"], pending["place"], pending["contributor"]),
                         (item["id"], self.place.pk, self.owner.username))
        item_list = f"/api/places/items/?place={self.place.pk}"
        item_action = f"/api/admin/items/{item['id']}/"
        price_list = f"/api/places/items/{item['id']}/prices/"
        first = self.admin.get("/api/admin/item-prices/?status=pending").data[0]
        first_action = f"/api/admin/item-prices/{first['id']}/"
        self.assertEqual(first["item_status"], "pending")
        self.assertEqual(self.client.get(item_list).data, [])
        self.post(self.admin, first_action + "approve/", expected=400)
        self.post(self.admin, item_action + "reject/", expected=400)
        self.post(self.admin, item_action + "reject/", {"reason": "Please confirm the menu."})
        self.assertEqual(self.client.get(item_list).data, [])
        self.post(self.admin, item_action + "approve/")
        self.assertIsNone(self.client.get(item_list).data[0]["average_price"])
        self.post(self.admin, first_action + "approve/")
        newer = self.as_user(self.other)
        second = self.post(newer, price_list, {"price": "35.00", "submitted_by": self.owner.pk}, 201)
        action = f"/api/admin/item-prices/{second['id']}/"
        self.post(self.admin, action + "reject/", {"reason": "Price unclear"})
        self.assertEqual([r["price"] for r in self.client.get(price_list).data], ["25.00"])
        history = newer.get("/api/accounts/submissions/").data
        self.assertEqual((history[0]["place_name"], history[0]["rejection_reason"]), (self.place.name, "Price unclear"))
        self.post(self.admin, action + "approve/")
        self.assertEqual(self.client.get(item_list).data[0]["average_price"], "30.00")
        self.assertEqual({r["submitted_by"] for r in self.client.get(price_list).data}, {self.owner.pk, self.other.pk})
        self.assertEqual(self.client.get(f"/api/places/items/?place={self.place.pk + 1000}").data, [])
        self.assertEqual(self.client.get("/api/places/items/?place=unknown").status_code, 400)

    def test_review_queue_public_rating_and_rejection_reason(self):
        path = f"/api/places/{self.place.pk}/reviews/"
        review = self.post(self.member, path, {"rating": 4, "comment": "Quiet in the morning."}, 201)
        action = f"/api/admin/reviews/{review['id']}/"
        self.assertEqual(self.admin.get("/api/admin/stats/").data["pending_reviews"], 1)
        row = self.admin.get("/api/admin/reviews/?status=pending").data[0]
        self.assertEqual((row["username"], row["place_name"]), (self.owner.username, self.place.name))
        self.post(self.admin, action + "reject/", {"reason": "Please clarify the visit."})
        self.assertEqual(self.member.get(path + "mine/").data["rejection_reason"], "Please clarify the visit.")
        self.assertEqual(self.client.get(path).data, [])
        self.member.patch(path + str(review["id"]) + "/", {"comment": "I visited at 8 am."}, format="json")
        self.post(self.admin, action + "approve/")
        details = self.client.get(f"/api/places/{self.place.pk}/").data
        self.assertEqual((details["review_count"], details["average_rating"]), (1, "4.00"))
        self.assertEqual(self.client.get(path).data[0]["user"], self.owner.pk)
        self.assertEqual(self.admin.get("/api/admin/stats/").data["pending_reviews"], 0)
