from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Skill,CandidateSkill,JobSkill
from .serializers import SkillSerializer,CandidateSkillSerializer,JobSkillSerializer
from apps.common import RolePermission
class SkillViewSet(viewsets.ModelViewSet):
    queryset=Skill.objects.all().order_by("name"); serializer_class=SkillSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","HR","TEAM_LEAD")
class CandidateSkillViewSet(viewsets.ModelViewSet):
    queryset=CandidateSkill.objects.select_related("candidate","skill").all(); serializer_class=CandidateSkillSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","HR","TEAM_LEAD")
class JobSkillViewSet(viewsets.ModelViewSet):
    queryset=JobSkill.objects.select_related("job","skill").all(); serializer_class=JobSkillSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","HR","TEAM_LEAD")
