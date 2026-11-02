from decimal import Decimal

from apps.sales.models import SalesOpportunity
from apps.testkit import SynfoAPITestCase, make_client


class SalesOpportunityApiTests(SynfoAPITestCase):
    def test_expected_value_follows_opportunity_visibility(self):
        own_client = make_client(self.sales, "Opportunity Own")
        other_client = make_client(self.sales_two, "Opportunity Other")
        self.as_user(self.sales)
        created = self.client.post(
            "/api/v1/sales-opportunities/",
            {
                "client": str(own_client.id),
                "title": "Own deal",
                "expected_value": "15000.00",
                "owner": str(self.sales_two.id),
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(str(created.data["owner"]), str(self.sales.id))
        self.assertEqual(created.data["expected_value"], "15000.00")
        hidden = SalesOpportunity.objects.create(
            client=other_client,
            owner=self.sales_two,
            title="Hidden deal",
            expected_value=Decimal("999.00"),
        )
        listing = self.client.get("/api/v1/sales-opportunities/")
        self.assertEqual({row["title"] for row in listing.data["results"]}, {"Own deal"})
        self.assertEqual(self.client.get(f"/api/v1/sales-opportunities/{hidden.id}/").status_code, 404)
        moved = self.client.patch(
            f"/api/v1/sales-opportunities/{created.data['id']}/",
            {"owner": str(self.management.id), "expected_value": "16000.00"},
            format="json",
        )
        self.assertEqual(moved.status_code, 200, moved.data)
        self.assertEqual(str(moved.data["owner"]), str(self.sales.id))
        self.assertEqual(moved.data["expected_value"], "16000.00")

        self.as_user(self.hr)
        self.assertEqual(self.client.get("/api/v1/sales-opportunities/").status_code, 403)
        self.as_user(self.management)
        visible = self.client.get("/api/v1/sales-opportunities/")
        values = {row["title"]: row["expected_value"] for row in visible.data["results"]}
        self.assertEqual(values["Hidden deal"], "999.00")
        self.assertEqual(values["Own deal"], "16000.00")
        reassigned = self.client.patch(
            f"/api/v1/sales-opportunities/{created.data['id']}/",
            {"owner": str(self.sales_two.id)},
            format="json",
        )
        self.assertEqual(reassigned.status_code, 200, reassigned.data)
        self.assertEqual(str(reassigned.data["owner"]), str(self.sales_two.id))
