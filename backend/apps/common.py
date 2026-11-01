from rest_framework.permissions import BasePermission, DjangoModelPermissions


class ModelActionPermission(DjangoModelPermissions):
    """Model permissions, including view, plus per-action overrides.

    Active superusers pass because ``User.has_perm`` returns True for them.
    Inactive users fail ``has_perm`` and cannot authenticate.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        action = getattr(view, "action", None)
        extra = getattr(view, "action_permissions", {})
        if action and action in extra:
            needed = extra[action]
            if isinstance(needed, str):
                return user.has_perm(needed)
            return user.has_perms(needed)
        return super().has_permission(request, view)


class RequiresPermission(BasePermission):
    """For APIView endpoints. Set ``required_permission = 'app.codename'``."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        permission = getattr(view, "required_permission", None)
        if not permission:
            return False
        return user.has_perm(permission)
