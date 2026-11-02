from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

from apps.billing.models import CreditNote, Invoice
from apps.testkit import SynfoAPITestCase, make_client


class BillingServiceTests(SynfoAPITestCase):
    def test_totals_payments_and_credit_notes_stay_in_step(self):
        client = make_client(self.management, "Billed Client")
        today = timezone.localdate().isoformat()
        self.as_user(self.hr)
        self.assertEqual(self.client.get("/api/v1/credit-notes/").status_code, 403)
        self.as_user(self.management)
        created = self.client.post(
            "/api/v1/invoices/",
            {
                "client": str(client.id),
                "invoice_date": today,
                "due_date": today,
                "subtotal": "9999.00",
                "tax_amount": "1.00",
                "total": "10000.00",
                "status": "ISSUED",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["subtotal"], "0.00")
        self.assertEqual(created.data["tax_amount"], "0.00")
        self.assertEqual(created.data["total"], "0.00")
        self.assertEqual(created.data["status"], "ISSUED")
        derived = self.client.post(
            "/api/v1/invoices/",
            {
                "client": str(client.id),
                "invoice_date": today,
                "due_date": today,
                "status": "PAID",
            },
            format="json",
        )
        self.assertEqual(derived.status_code, 400, derived.data)

        line = self.client.post(
            "/api/v1/invoice-lines/",
            {
                "invoice": created.data["id"],
                "description": "Placement fee",
                "quantity": 2,
                "unit_amount": "1000.00",
                "tax_rate": "18.00",
            },
            format="json",
        )
        self.assertEqual(line.status_code, 201, line.data)
        invoice = Invoice.objects.get(pk=created.data["id"])
        self.assertEqual(invoice.subtotal, Decimal("2000.00"))
        self.assertEqual(invoice.tax_amount, Decimal("360.00"))
        self.assertEqual(invoice.total, Decimal("2360.00"))

        payment = self.client.post(
            "/api/v1/payments/",
            {"invoice": created.data["id"], "amount": "1000.00", "payment_date": today},
            format="json",
        )
        self.assertEqual(payment.status_code, 201, payment.data)
        raised = self.client.patch(
            f"/api/v1/payments/{payment.data['id']}/",
            {"amount": "1500.00"},
            format="json",
        )
        self.assertEqual(raised.status_code, 200, raised.data)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "PART_PAID")
        self.assertEqual(invoice.outstanding_amount, Decimal("860.00"))

        note = self.client.post(
            "/api/v1/credit-notes/",
            {
                "invoice": created.data["id"],
                "amount": "860.00",
                "reason": "Fee adjustment",
                "issue_date": today,
            },
            format="json",
        )
        self.assertEqual(note.status_code, 201, note.data)
        self.assertTrue(note.data["credit_note_number"].startswith(f"SW-CN-{timezone.localdate().year}-"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "PAID")
        self.assertEqual(invoice.outstanding_amount, Decimal("0.00"))
        self.assertEqual(invoice.credited_amount, Decimal("860.00"))
        too_much = self.client.post(
            "/api/v1/credit-notes/",
            {
                "invoice": created.data["id"],
                "amount": "1.00",
                "reason": "Too much",
                "issue_date": today,
            },
            format="json",
        )
        self.assertEqual(too_much.status_code, 400, too_much.data)
        self.assertEqual(CreditNote.objects.filter(invoice=invoice).count(), 1)

        second = self.client.post(
            "/api/v1/invoices/",
            {"client": str(client.id), "invoice_date": today, "due_date": today, "status": "ISSUED"},
            format="json",
        )
        self.client.post(
            "/api/v1/invoice-lines/",
            {
                "invoice": second.data["id"],
                "description": "Open balance",
                "quantity": 1,
                "unit_amount": "100.00",
                "tax_rate": "0.00",
            },
            format="json",
        )
        before = CreditNote.objects.count()
        with patch("apps.billing.services.apply_payment_status", side_effect=RuntimeError("fail")):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    "/api/v1/credit-notes/",
                    {
                        "invoice": second.data["id"],
                        "amount": "10.00",
                        "reason": "Should roll back",
                        "issue_date": today,
                    },
                    format="json",
                )
        self.assertEqual(CreditNote.objects.count(), before)
