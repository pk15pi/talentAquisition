from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access import user_has

from .models import SystemConfiguration
from .serializers import SystemConfigurationSerializer


class SystemConfigurationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        if not user_has(request.user, "organizations.view_systemconfiguration"):
            raise PermissionDenied("You do not have permission to view system configuration.")
        return Response(SystemConfigurationSerializer(SystemConfiguration.load()).data)

    def patch(self, request, **kwargs):
        if not user_has(request.user, "organizations.change_systemconfiguration"):
            raise PermissionDenied("You do not have permission to change system configuration.")
        obj = SystemConfiguration.load()
        serializer = SystemConfigurationSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)
