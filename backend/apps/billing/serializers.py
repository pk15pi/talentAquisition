from rest_framework import serializers

from .models import CreditNote, Invoice, InvoiceLine, Payment
from .services import issue_credit_note, remaining_capacity, update_credit_note

DERIVED_INVOICE_STATUSES = {Invoice.Status.PAID, Invoice.Status.PART_PAID}


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = "__all__"

    def validate_unit_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit amount cannot be negative.")
        return value

    def validate_tax_rate(self, value):
        if value < 0:
            raise serializers.ValidationError("Tax rate cannot be negative.")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    credited_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = (
            "id",
            "invoice_number",
            "created_by",
            "created_at",
            "subtotal",
            "tax_amount",
            "total",
        )

    def validate_status(self, value):
        if value in DERIVED_INVOICE_STATUSES:
            raise serializers.ValidationError(
                "Paid and part-paid are derived from payments and credit notes."
            )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["client_name"] = instance.client.company_name if instance.client_id else ""
        data["client_code"] = instance.client.client_code if instance.client_id else ""
        return data


class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("recorded_by", "invoice_number")

    def validate(self, attrs):
        invoice = attrs.get("invoice", getattr(self.instance, "invoice", None))
        amount = attrs.get("amount", getattr(self.instance, "amount", 0))
        if invoice and amount > remaining_capacity(invoice, exclude_payment=self.instance):
            raise serializers.ValidationError("Payment cannot exceed the invoice outstanding amount.")
        return attrs


class CreditNoteSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)

    class Meta:
        model = CreditNote
        fields = "__all__"
        read_only_fields = ("id", "credit_note_number", "created_by", "invoice_number")

    def validate(self, attrs):
        if self.instance is not None and "invoice" in attrs and attrs["invoice"].pk != self.instance.invoice_id:
            raise serializers.ValidationError({"invoice": "A credit note cannot be moved to another invoice."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        return issue_credit_note(
            invoice=validated_data["invoice"],
            amount=validated_data["amount"],
            reason=validated_data["reason"],
            issue_date=validated_data["issue_date"],
            user=request.user,
        )

    def update(self, instance, validated_data):
        validated_data.pop("invoice", None)
        return update_credit_note(instance, **validated_data)
