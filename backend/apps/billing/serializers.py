from rest_framework import serializers
from .models import Invoice,InvoiceLine,Payment
class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta: model=InvoiceLine; fields="__all__"
class InvoiceSerializer(serializers.ModelSerializer):
    lines=InvoiceLineSerializer(many=True,read_only=True)
    paid_amount=serializers.DecimalField(max_digits=12,decimal_places=2,read_only=True)
    outstanding_amount=serializers.DecimalField(max_digits=12,decimal_places=2,read_only=True)
    class Meta: model=Invoice; fields="__all__"; read_only_fields=("id","invoice_number","created_by","created_at")
class PaymentSerializer(serializers.ModelSerializer):
    class Meta: model=Payment; fields="__all__"; read_only_fields=("recorded_by",)
    def validate(self,attrs):
        invoice=attrs.get("invoice", getattr(self.instance,"invoice",None))
        amount=attrs.get("amount", getattr(self.instance,"amount",0))
        if invoice and amount > invoice.outstanding_amount:
            raise serializers.ValidationError("Payment cannot exceed the invoice outstanding amount.")
        return attrs
