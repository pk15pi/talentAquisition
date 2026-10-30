from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.access import user_has, visible_clients
from apps.common import ModelActionPermission

from .models import Client, ClientActivity, ClientContact, ClientOwnershipHistory
from .serializers import ClientActivitySerializer, ClientContactSerializer, ClientSerializer


class ClientViewSet(ModelViewSet):
    queryset = Client.objects.select_related("sales_owner", "created_by").prefetch_related("contacts").all().order_by("-created_at")
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def get_queryset(self):
        return visible_clients(self.request.user).select_related("sales_owner", "created_by").prefetch_related("contacts").order_by("-created_at")

    def perform_create(self, serializer):
        owner = serializer.validated_data.get("sales_owner")
        if owner is None or not user_has(self.request.user, "clients.assign_client_owner"):
            owner = self.request.user
        if not owner.is_active or not owner.has_perm("clients.own_client"):
            raise ValidationError({"sales_owner": "Choose an active user who is allowed to own clients."})
        client = serializer.save(created_by=self.request.user, sales_owner=owner)
        ClientOwnershipHistory.objects.create(
            client=client,
            old_owner=None,
            new_owner=owner,
            changed_by=self.request.user,
            remarks="Initial client ownership",
        )

    def perform_update(self, serializer):
        old_owner = serializer.instance.sales_owner
        new_owner = serializer.validated_data.get("sales_owner", old_owner)
        if not user_has(self.request.user, "clients.assign_client_owner"):
            new_owner = old_owner
        elif not new_owner.is_active or not new_owner.has_perm("clients.own_client"):
            raise ValidationError({"sales_owner": "Choose an active user who is allowed to own clients."})
        client = serializer.save(sales_owner=new_owner)
        if old_owner.pk != client.sales_owner_id:
            ClientOwnershipHistory.objects.create(
                client=client,
                old_owner=old_owner,
                new_owner=client.sales_owner,
                changed_by=self.request.user,
                remarks="Client ownership changed",
            )


class ClientContactViewSet(ModelViewSet):
    queryset = ClientContact.objects.select_related("client").all()
    serializer_class = ClientContactSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def get_queryset(self):
        return ClientContact.objects.select_related("client").filter(client__in=visible_clients(self.request.user))

    def perform_create(self, serializer):
        client = serializer.validated_data["client"]
        if not visible_clients(self.request.user).filter(pk=client.pk).exists():
            raise PermissionDenied("You cannot add contacts to this client.")
        serializer.save()


class ClientActivityViewSet(ModelViewSet):
    queryset = ClientActivity.objects.select_related("client", "user").all().order_by("-created_at")
    serializer_class = ClientActivitySerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def get_queryset(self):
        return (
            ClientActivity.objects.select_related("client", "user")
            .filter(client__in=visible_clients(self.request.user))
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        client = serializer.validated_data["client"]
        if not visible_clients(self.request.user).filter(pk=client.pk).exists():
            raise PermissionDenied("You cannot add activities to this client.")
        serializer.save(user=self.request.user)
