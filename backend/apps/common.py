from rest_framework.permissions import BasePermission
class RolePermission(BasePermission):
    """Simple role gate; queryset filtering and object-level checks remain view-specific."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated: return False
        allowed=getattr(view,"allowed_roles",None)
        return not allowed or request.user.is_superuser or request.user.role in allowed
