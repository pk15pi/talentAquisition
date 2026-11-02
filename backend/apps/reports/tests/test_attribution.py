from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.billing.models import Invoice
from apps.clients.models import ClientOwnershipHistory
from apps.testkit import SynfoAPITestCase, make_client


class HistoricalReportTests(SynfoAPITestCase):
    def test_client_credit_stays_with_the_creation_owner(self):
        self.as_user(self.management)
        created = self.client.post(
            "/api/v1/clients/",
            {"company_name": "Historical Co", "sales_owner": str(self.sales.id)},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        moved = self.client.patch(
            f"/api/v1/clients/{created.data['id']}/",
            {"sales_owner": str(self.sales_two.id)},
            format="json",
        )
        self.assertEqual(moved.status_code, 200, moved.data)
        report = self.client.get("/api/v1/reports/sales/")
        self.assertEqual(report.status_code, 200, report.data)
        credited = {str(row["sales_owner__id"]): row["clients"] for row in report.data["clients_by_sales_owner"]}
        self.assertGreaterEqual(credited.get(str(self.sales.id), 0), 1)
        self.assertNotIn(str(self.sales_two.id), credited)
        self.assertEqual(report.data["attribution"]["clients"], "owner_at_creation")
        self.assertEqual(report.data["attribution"]["jobs"], "current_sales_owner")

    def test_invoice_credit_uses_the_owner_at_invoice_time(self):
        client = make_client(self.sales_two, "Invoiced Co")
        earlier = timezone.now() - timedelta(days=20)
        later = timezone.now() - timedelta(days=1)
        first = ClientOwnershipHistory.objects.create(
            client=client,
            old_owner=None,
            new_owner=self.sales,
            changed_by=self.management,
            remarks="Initial",
        )
        second = ClientOwnershipHistory.objects.create(
            client=client,
            old_owner=self.sales,
            new_owner=self.sales_two,
            changed_by=self.management,
            remarks="Transfer",
        )
        ClientOwnershipHistory.objects.filter(pk=first.pk).update(changed_at=earlier)
        ClientOwnershipHistory.objects.filter(pk=second.pk).update(changed_at=later)
        invoice = Invoice.objects.create(
            client=client,
            invoice_date="2026-10-01",
            due_date="2026-10-15",
            created_by=self.management,
            subtotal=Decimal("250.00"),
            tax_amount=Decimal("0.00"),
            total=Decimal("250.00"),
            status="ISSUED",
        )
        Invoice.objects.filter(pk=invoice.pk).update(created_at=earlier + timedelta(days=1))
        self.as_user(self.management)
        report = self.client.get("/api/v1/reports/sales/")
        rows = {str(row["sales_owner__id"]): row["invoiced_total"] for row in report.data["invoiced_by_owner"]}
        self.assertEqual(rows[str(self.sales.id)], "250.00")
        self.as_user(self.hr)
        hr_report = self.client.get("/api/v1/reports/hr/")
        self.assertEqual(hr_report.status_code, 200, hr_report.data)
        self.assertNotIn("invoiced_revenue", hr_report.data)
        self.assertNotIn("invoiced_by_owner", hr_report.data)
        self.assertNotIn("expected_revenue", hr_report.data)

    def test_date_and_bad_status_filters(self):
        self.as_user(self.management)
        refused = self.client.get("/api/v1/reports/overview/", {"status": "NOT_A_STATUS"})
        self.assertEqual(refused.status_code, 400, refused.data)
        empty = self.client.get("/api/v1/reports/overview/", {"date_from": "1999-01-01", "date_to": "1999-01-02"})
        self.assertEqual(empty.status_code, 200, empty.data)
        self.assertEqual(empty.data["clients"], 0)
        self.assertEqual(empty.data["invoiced_revenue"], 0)
        self.as_user(self.hr)
        hidden = self.client.get("/api/v1/reports/overview/", {"date_from": "1999-01-01", "date_to": "1999-01-02"})
        self.assertEqual(hidden.data["invoiced_revenue"], 0)
