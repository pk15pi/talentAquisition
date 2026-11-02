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

    def _assignable_owner(self, serializer):
        from apps.access import user_has

        current = serializer.instance.owner if serializer.instance is not None else None
        requested = serializer.validated_data.get("owner", current)
        if requested is None or not user_has(self.request.user, "sales.view_all_salesopportunity"):
            return self.request.user if serializer.instance is None else current
        if not requested.is_active:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"owner": "Choose an active user."})
        return requested

    def perform_create(self, serializer):
        serializer.save(owner=self._assignable_owner(serializer))

    def perform_update(self, serializer):
        serializer.save(owner=self._assignable_owner(serializer))
