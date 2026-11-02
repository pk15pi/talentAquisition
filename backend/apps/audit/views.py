from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.common import RequiresPermission

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(ReadOnlyModelViewSet):
    """Operator log. Requires the Django audit.view_auditlog permission."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, RequiresPermission]
    required_permission = "audit.view_auditlog"

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("user").order_by("-timestamp")
        action = (self.request.query_params.get("action") or "").strip()
        if action:
            queryset = queryset.filter(action=action)
        return queryset
