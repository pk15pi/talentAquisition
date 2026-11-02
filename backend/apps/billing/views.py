from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.common import ModelActionPermission

from .models import CreditNote, Invoice, InvoiceLine, Payment
from .serializers import CreditNoteSerializer, InvoiceLineSerializer, InvoiceSerializer, PaymentSerializer
from .services import audit_billing, remaining_capacity


class InvoiceViewSet(ModelViewSet):
    queryset = Invoice.objects.prefetch_related("lines", "payments", "credit_notes").all().order_by("-created_at")
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def perform_create(self, serializer):
        with transaction.atomic():
            invoice = serializer.save(created_by=self.request.user)
            audit_billing(self.request.user, "invoice_saved", invoice, {"total": str(invoice.total), "created": True})

    def perform_update(self, serializer):
        with transaction.atomic():
            invoice = serializer.save()
            audit_billing(self.request.user, "invoice_saved", invoice, {"total": str(invoice.total), "created": False})


class InvoiceLineViewSet(ModelViewSet):
    queryset = InvoiceLine.objects.select_related("invoice", "placement").all()
    serializer_class = InvoiceLineSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def perform_create(self, serializer):
        with transaction.atomic():
            line = serializer.save()
            audit_billing(
                self.request.user,
                "invoice_line_saved",
                line,
                {"invoice_id": str(line.invoice_id), "created": True},
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            line = serializer.save()
            audit_billing(
                self.request.user,
                "invoice_line_saved",
                line,
                {"invoice_id": str(line.invoice_id), "created": False},
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            audit_billing(
                self.request.user,
                "invoice_line_deleted",
                instance,
                {"invoice_id": str(instance.invoice_id)},
            )
            instance.delete()


class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.select_related("invoice").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def perform_create(self, serializer):
        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(pk=serializer.validated_data["invoice"].pk)
            amount = serializer.validated_data["amount"]
            if amount > remaining_capacity(invoice):
                raise ValidationError("Payment cannot exceed the invoice outstanding amount.")
            payment = serializer.save(recorded_by=self.request.user)
            audit_billing(self.request.user, "payment_saved", payment, {"invoice_id": str(invoice.pk), "amount": str(payment.amount)})

    def perform_update(self, serializer):
        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(pk=serializer.instance.invoice_id)
            amount = serializer.validated_data.get("amount", serializer.instance.amount)
            if amount > remaining_capacity(invoice, exclude_payment=serializer.instance):
                raise ValidationError("Payment cannot exceed the invoice outstanding amount.")
            payment = serializer.save()
            audit_billing(self.request.user, "payment_saved", payment, {"invoice_id": str(invoice.pk), "amount": str(payment.amount)})


class CreditNoteViewSet(ModelViewSet):
    queryset = CreditNote.objects.select_related("invoice", "created_by").order_by("-issue_date")
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
