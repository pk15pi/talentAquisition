from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from apps.applications.models import Application
from apps.placements.models import Placement
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class FinancePermissionTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        candidate = make_candidate(self.hr, email="fee@example.com", phone="9666666666")
        job = make_job(make_client(self.sales, "Fee Co"), self.sales, "Fee JD")
        application = Application.objects.create(candidate=candidate, job=job, recruiter=self.hr, status="OFFERED")
        self.placement = Placement.objects.create(
            application=application,
            offered_ctc=Decimal("1200000.00"),
            agreed_fee_type="PERCENTAGE",
            agreed_fee_value=Decimal("8.33"),
            expected_revenue=Decimal("100000.00"),
        )

    def test_hr_sees_placement_without_commercial_fields_and_cannot_open_invoices(self):
        self.as_user(self.hr)
        placement = self.client.get(f"/api/v1/placements/{self.placement.id}/")
        self.assertEqual(placement.status_code, 200, placement.data)
        self.assertNotIn("offered_ctc", placement.data)
        self.assertNotIn("expected_revenue", placement.data)
        self.assertNotIn("agreed_fee_value", placement.data)
        self.assertEqual(placement.data["status"], "OFFERED")
        invoices = self.client.get("/api/v1/invoices/")
        self.assertEqual(invoices.status_code, 403)
        created = self.client.post(
            "/api/v1/placements/",
            {
                "application": str(self.placement.application_id),
                "offered_ctc": "1000.00",
                "agreed_fee_type": "FIXED",
                "agreed_fee_value": "100.00",
                "expected_revenue": "100.00",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 403)
        report = self.client.get("/api/v1/reports/overview/")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.data["invoiced_revenue"], 0)

    def test_management_sees_commercial_fields(self):
        self.as_user(self.management)
        placement = self.client.get(f"/api/v1/placements/{self.placement.id}/")
        self.assertEqual(placement.data["offered_ctc"], "1200000.00")
        self.assertEqual(placement.data["expected_revenue"], "100000.00")
        invoices = self.client.get("/api/v1/invoices/")
        self.assertEqual(invoices.status_code, 200)

    def test_invoice_access_follows_the_permission_not_the_role_label(self):
        User = get_user_model()
        self.management.groups.clear()
        self.management.user_permissions.clear()
        user = User.objects.get(pk=self.management.pk)
        self.assertEqual(user.role, "MANAGEMENT")
        self.as_user(user)
        self.assertEqual(self.client.get("/api/v1/invoices/").status_code, 403)
        perm = Permission.objects.get(content_type__app_label="billing", codename="view_invoice")
        user.user_permissions.add(perm)
        user = User.objects.get(pk=user.pk)
        self.as_user(user)
        self.assertEqual(self.client.get("/api/v1/invoices/").status_code, 200)
