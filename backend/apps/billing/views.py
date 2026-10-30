from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Invoice,Payment,InvoiceLine
from .serializers import InvoiceSerializer,PaymentSerializer,InvoiceLineSerializer
from apps.common import RolePermission
class InvoiceViewSet(viewsets.ModelViewSet):
    queryset=Invoice.objects.prefetch_related("lines","payments").all().order_by("-created_at"); serializer_class=InvoiceSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT")
    def perform_create(self,serializer): serializer.save(created_by=self.request.user)
class InvoiceLineViewSet(viewsets.ModelViewSet):
    queryset=InvoiceLine.objects.select_related("invoice","placement").all(); serializer_class=InvoiceLineSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT")
class PaymentViewSet(viewsets.ModelViewSet):
    queryset=Payment.objects.select_related("invoice").all(); serializer_class=PaymentSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT")
    def perform_create(self,serializer): serializer.save(recorded_by=self.request.user)
