from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer
class UserViewSet(viewsets.ModelViewSet):
    queryset=User.objects.all().order_by("first_name","last_name")
    serializer_class=UserSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.role in ("ADMIN","MANAGEMENT","TEAM_LEAD"):
            return super().get_queryset()
        return User.objects.filter(id=self.request.user.id)
    def create(self,request,*args,**kwargs):
        if not (request.user.is_superuser or request.user.role=="ADMIN"):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only administrators can create users.")
        return super().create(request,*args,**kwargs)
    def update(self,request,*args,**kwargs):
        if not (request.user.is_superuser or request.user.role=="ADMIN"):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only administrators can update users.")
        return super().update(request,*args,**kwargs)
    def destroy(self,request,*args,**kwargs):
        if not (request.user.is_superuser or request.user.role=="ADMIN"):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only administrators can deactivate users.")
        user=self.get_object(); user.is_active=False; user.save(update_fields=["is_active"])
        from rest_framework.response import Response
        return Response(status=204)
