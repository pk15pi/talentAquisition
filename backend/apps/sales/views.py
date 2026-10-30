from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import SalesOpportunity
from .serializers import SalesOpportunitySerializer
class SalesOpportunityViewSet(viewsets.ModelViewSet):
    queryset=SalesOpportunity.objects.select_related("client","owner").all().order_by("-created_at")
    serializer_class=SalesOpportunitySerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        qs=super().get_queryset()
        if self.request.user.role=="SALES": return qs.filter(owner=self.request.user)
        return qs
    def perform_create(self,serializer):
        owner=self.request.user if self.request.user.role=="SALES" else serializer.validated_data.get("owner",self.request.user)
        serializer.save(owner=owner)
