"""Write AuditLog rows. Callers pass the actor and a JSON-safe details dict."""

from apps.audit.models import AuditLog


def record_audit(*, user, action, entity_type, entity_id="", details=None, ip_address=None):
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", True) else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id or ""),
        details=details or {},
        ip_address=ip_address,
    )


def request_ip(request):
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR") or None
