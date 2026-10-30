from rest_framework.routers import DefaultRouter
from .views import SkillViewSet,CandidateSkillViewSet,JobSkillViewSet
router=DefaultRouter(); router.register("skills",SkillViewSet); router.register("candidate-skills",CandidateSkillViewSet); router.register("job-skills",JobSkillViewSet)
urlpatterns=router.urls
