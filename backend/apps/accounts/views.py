from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.access import user_has

from .models import User
from .serializers import UserSerializer


class UserAccess(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        action_name = getattr(view, "action", None)
        if action_name == "create":
            return user.has_perm("accounts.add_user")
        if action_name in ("update", "partial_update"):
            return user.has_perm("accounts.change_user")
        if action_name == "destroy":
            return user.has_perm("accounts.delete_user")
        if action_name in ("list", "retrieve", "me", None):
            return True
        return user.has_perm("accounts.view_user")


class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("first_name", "last_name")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, UserAccess]

    def get_queryset(self):
        if user_has(self.request.user, "accounts.view_user"):
            return super().get_queryset()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=["get"])
    def me(self, request, **kwargs):
        return Response(self.get_serializer(request.user).data)

    def destroy(self, request, *args, **kwargs):
        if not user_has(request.user, "accounts.delete_user"):
            raise PermissionDenied("You do not have permission to deactivate users.")
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=204)
