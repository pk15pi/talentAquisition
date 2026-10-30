from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Client, ClientContact, ClientOwnershipHistory, ClientActivity
from .serializers import ClientSerializer, ClientContactSerializer, ClientActivitySerializer
from apps.common import RolePermission

class ClientViewSet(viewsets.ModelViewSet):
    queryset=Client.objects.select_related("sales_owner","created_by").prefetch_related("contacts").all().order_by("-created_at")
    serializer_class=ClientSerializer
    permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","SALES","HR","TEAM_LEAD")
    def get_queryset(self):
        qs=super().get_queryset()
        if self.request.user.role=="SALES": return qs.filter(sales_owner=self.request.user)
        return qs
    def perform_create(self,serializer):
        from rest_framework.exceptions import PermissionDenied, ValidationError
        if self.request.user.role=="SALES": owner=self.request.user
        elif self.request.user.role in ("ADMIN","MANAGEMENT"):
            owner=serializer.validated_data.get("sales_owner")
            if not owner or owner.role != "SALES": raise ValidationError({"sales_owner":"Select an active Sales Executive as the client owner."})
        else: raise PermissionDenied("Only Sales, Management or Admin can create clients.")
        client=serializer.save(created_by=self.request.user,sales_owner=owner)
        ClientOwnershipHistory.objects.create(client=client,old_owner=None,new_owner=owner,changed_by=self.request.user,remarks="Initial client ownership")
    def perform_update(self,serializer):
        old_owner=serializer.instance.sales_owner
        if self.request.user.role not in ("ADMIN","MANAGEMENT"): client=serializer.save(sales_owner=old_owner)
        else: client=serializer.save()
        if old_owner.pk != client.sales_owner_id:
            ClientOwnershipHistory.objects.create(client=client,old_owner=old_owner,new_owner=client.sales_owner,changed_by=self.request.user,remarks="Client ownership changed")

class ClientContactViewSet(viewsets.ModelViewSet):
    queryset=ClientContact.objects.select_related("client").all()
    serializer_class=ClientContactSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        qs=super().get_queryset()
        if self.request.user.role=="SALES": return qs.filter(client__sales_owner=self.request.user)
        return qs

class ClientActivityViewSet(viewsets.ModelViewSet):
    queryset=ClientActivity.objects.select_related("client","user").all().order_by("-created_at")
    serializer_class=ClientActivitySerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        qs=super().get_queryset()
        if self.request.user.role=="SALES": return qs.filter(client__sales_owner=self.request.user)
        return qs
    def perform_create(self,serializer): serializer.save(user=self.request.user)
