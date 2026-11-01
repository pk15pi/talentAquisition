from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.access import visible_opportunities
from apps.common import ModelActionPermission

from .models import SalesOpportunity
from .serializers import SalesOpportunitySerializer


class SalesOpportunityViewSet(ModelViewSet):
    queryset = SalesOpportunity.objects.select_related("client", "owner").all().order_by("-created_at")
    serializer_class = SalesOpportunitySerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def get_queryset(self):
        return visible_opportunities(self.request.user).select_related("client", "owner").order_by("-created_at")

    def perform_create(self, serializer):
        from apps.access import user_has

        owner = serializer.validated_data.get("owner")
        if owner is None or not user_has(self.request.user, "sales.view_all_salesopportunity"):
            owner = self.request.user
        serializer.save(owner=owner)
