from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Placement
from .serializers import PlacementSerializer
from apps.common import RolePermission
class PlacementViewSet(viewsets.ModelViewSet):
    queryset=Placement.objects.select_related("application").all(); serializer_class=PlacementSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","HR","TEAM_LEAD")
