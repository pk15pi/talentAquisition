from decimal import Decimal

from apps.applications.models import Application
from apps.placements.models import Placement
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class PlacementCommercialTermTests(SynfoAPITestCase):
    def _application(self, client, title):
        candidate = make_candidate(
            self.hr,
            email=f"{title}@example.com",
            phone="900111" + str(abs(hash(title)) % 10000).zfill(4),
            name=title,
        )
        job = make_job(client, self.sales, title)
        return Application.objects.create(candidate=candidate, job=job, recruiter=self.hr), job

    def test_create_copies_effective_terms_and_derives_revenue(self):
        client = make_client(self.sales, "Terms Co")
        client.default_fee_type = "PERCENTAGE"
        client.default_fee_value = Decimal("10.00")
        client.default_guarantee_period_days = 45
        client.save()
        application, job = self._application(client, "Copied")
        self.assertFalse(self.hr.has_perm("placements.add_placement"))
        self.assertFalse(self.hr.has_perm("placements.change_placement"))
        self.assertFalse(self.hr.has_perm("placements.change_placement_financials"))
        self.as_user(self.hr)
        refused = self.client.post(
            "/api/v1/placements/",
            {"application": str(application.id), "offered_ctc": "1000000.00"},
            format="json",
        )
        self.assertEqual(refused.status_code, 403)
        self.as_user(self.management)
        created = self.client.post(
            "/api/v1/placements/",
            {"application": str(application.id), "offered_ctc": "1000000.00"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["agreed_fee_type"], "PERCENTAGE")
        self.assertEqual(created.data["agreed_fee_value"], "10.00")
        self.assertEqual(created.data["guarantee_period_days"], 45)
        self.assertEqual(created.data["expected_revenue"], "100000.00")

        job.fee_type = "FIXED"
        job.fee_value = Decimal("50000.00")
        job.guarantee_period_days = 30
        job.save()
        override_application, _job = self._application(client, "Override")
        override_application.job = job
        override_application.save()
        overridden = self.client.post(
            "/api/v1/placements/",
            {"application": str(override_application.id), "offered_ctc": "800000.00"},
            format="json",
        )
        self.assertEqual(overridden.status_code, 201, overridden.data)
        self.assertEqual(overridden.data["agreed_fee_type"], "FIXED")
        self.assertEqual(overridden.data["agreed_fee_value"], "50000.00")
        self.assertEqual(overridden.data["guarantee_period_days"], 30)
        self.assertEqual(overridden.data["expected_revenue"], "50000.00")

        explicit_application, _explicit_job = self._application(client, "Explicit")
        explicit = self.client.post(
            "/api/v1/placements/",
            {
                "application": str(explicit_application.id),
                "offered_ctc": "1000000.00",
                "agreed_fee_type": "PERCENTAGE",
                "agreed_fee_value": "12.50",
                "expected_revenue": "1.00",
                "guarantee_period_days": 10,
            },
            format="json",
        )
        self.assertEqual(explicit.status_code, 201, explicit.data)
        self.assertEqual(explicit.data["expected_revenue"], "1.00")
        self.assertEqual(explicit.data["guarantee_period_days"], 10)
        self.assertEqual(explicit.data["agreed_fee_value"], "12.50")

        updated = self.client.patch(
            f"/api/v1/placements/{created.data['id']}/",
            {"offered_ctc": "2000000.00"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["expected_revenue"], "200000.00")
        self.assertEqual(updated.data["agreed_fee_value"], "10.00")

        bare = make_client(self.sales, "No Terms")
        bare_application, _bare_job = self._application(bare, "Bare")
        missing = self.client.post(
            "/api/v1/placements/",
            {"application": str(bare_application.id), "offered_ctc": "1000.00"},
            format="json",
        )
        self.assertEqual(missing.status_code, 400, missing.data)
        self.assertFalse(Placement.objects.filter(application=bare_application).exists())

        self.as_user(self.hr)
        hidden = self.client.get(f"/api/v1/placements/{created.data['id']}/")
        self.assertEqual(hidden.status_code, 200, hidden.data)
        self.assertNotIn("offered_ctc", hidden.data)
        self.assertNotIn("expected_revenue", hidden.data)
        self.assertNotIn("agreed_fee_value", hidden.data)
        self.assertEqual(hidden.data["status"], "OFFERED")
