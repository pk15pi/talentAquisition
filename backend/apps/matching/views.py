from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.common import ModelActionPermission

from .models import CandidateSkill, JobSkill, Skill
from .serializers import CandidateSkillSerializer, JobSkillSerializer, SkillSerializer


class SkillViewSet(ModelViewSet):
    queryset = Skill.objects.all().order_by("name")
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]


class CandidateSkillViewSet(ModelViewSet):
    queryset = CandidateSkill.objects.select_related("candidate", "skill").all()
    serializer_class = CandidateSkillSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]


class JobSkillViewSet(ModelViewSet):
    queryset = JobSkill.objects.select_related("job", "skill").all()
    serializer_class = JobSkillSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
