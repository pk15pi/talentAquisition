from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.common import ModelActionPermission

from .models import Invoice, InvoiceLine, Payment
from .serializers import InvoiceLineSerializer, InvoiceSerializer, PaymentSerializer


class InvoiceViewSet(ModelViewSet):
    queryset = Invoice.objects.prefetch_related("lines", "payments").all().order_by("-created_at")
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InvoiceLineViewSet(ModelViewSet):
    queryset = InvoiceLine.objects.select_related("invoice", "placement").all()
    serializer_class = InvoiceLineSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]


class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.select_related("invoice").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)
