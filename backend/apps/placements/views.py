from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.common import ModelActionPermission

from .models import Placement
from .serializers import PlacementSerializer


class PlacementViewSet(ModelViewSet):
    queryset = Placement.objects.select_related("application").all()
    serializer_class = PlacementSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
