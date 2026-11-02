from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.audit.models import AuditLog
from apps.billing.admin import InvoiceAdmin, PaymentAdmin
from apps.billing.models import Invoice, InvoiceLine, Payment
from apps.testkit import SynfoAPITestCase, make_client


class BillingAdminIntegrityTests(SynfoAPITestCase):
    def test_admin_header_is_recomputed_and_overpayment_is_refused(self):
        client = make_client(self.management, "Admin Billing")
        invoice = Invoice.objects.create(
            client=client,
            invoice_date="2026-11-01",
            due_date="2026-11-15",
            created_by=self.management,
            subtotal=Decimal("999.00"),
            tax_amount=Decimal("0.00"),
            total=Decimal("999.00"),
        )
        request = RequestFactory().post("/admin/billing/invoice/")
        request.user = self.management
        InvoiceAdmin(Invoice, AdminSite()).save_model(request, invoice, form=None, change=True)
        invoice.refresh_from_db()
        self.assertEqual(invoice.total, Decimal("0.00"))
        self.assertIn("subtotal", InvoiceAdmin.readonly_fields)
        self.assertIn("total", InvoiceAdmin.readonly_fields)
        InvoiceLine.objects.create(
            invoice=invoice,
            description="Fee",
            quantity=2,
            unit_amount=Decimal("1000.00"),
            tax_rate=Decimal("18.00"),
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.total, Decimal("2360.00"))
        over = Payment(
            invoice=invoice,
            amount=Decimal("3000.00"),
            payment_date="2026-11-02",
            recorded_by=self.management,
        )
        with self.assertRaises(ValidationError):
            PaymentAdmin(Payment, AdminSite()).save_model(request, over, form=None, change=False)
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 0)
        allowed = Payment(
            invoice=invoice,
            amount=Decimal("1000.00"),
            payment_date="2026-11-02",
            recorded_by=self.management,
        )
        PaymentAdmin(Payment, AdminSite()).save_model(request, allowed, form=None, change=False)
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="payment_saved").exists())
