from django.utils import timezone
from rest_framework import viewsets,status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Job,JobAssignment,JobStatusHistory
from django.contrib.auth import get_user_model
from .serializers import JobSerializer
from apps.matching.services import run_matching
from apps.common import RolePermission
class JobViewSet(viewsets.ModelViewSet):
    queryset=Job.objects.select_related("client","sales_owner","created_by").prefetch_related("assignments").all().order_by("-created_at")
    serializer_class=JobSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","SALES","HR","TEAM_LEAD")
    def get_queryset(self):
        qs=super().get_queryset()
        if self.request.user.role=="SALES": return qs.filter(sales_owner=self.request.user)
        return qs
    def perform_create(self,serializer):
        client=serializer.validated_data["client"]
        owner=self.request.user if self.request.user.role == "SALES" else serializer.validated_data.get("sales_owner") or client.sales_owner
        job=serializer.save(created_by=self.request.user,sales_owner=owner)
        JobStatusHistory.objects.create(job=job,old_status="",new_status=job.status,changed_by=self.request.user,remarks="JD created")
    def perform_update(self,serializer):
        old_status=serializer.instance.status
        old_owner=serializer.instance.sales_owner
        if self.request.user.role not in ("ADMIN","MANAGEMENT"):
            job=serializer.save(sales_owner=old_owner)
        else:
            job=serializer.save()
        if old_status != job.status:
            JobStatusHistory.objects.create(job=job,old_status=old_status,new_status=job.status,changed_by=self.request.user)
    @action(detail=True,methods=["post"])
    def assign(self,request,pk=None):
        job=self.get_object()
        if not (request.user.is_superuser or request.user.role in ("ADMIN","MANAGEMENT","TEAM_LEAD")): return Response({"detail":"Only management or team leads can assign recruiters."},status=403)
        ids=request.data.get("recruiter_ids",[])
        if not isinstance(ids,list) or not ids: return Response({"detail":"recruiter_ids must be a non-empty list"},status=400)
        created=[]
        User=get_user_model()
        valid_ids=set(str(x) for x in User.objects.filter(id__in=ids,role__in=("HR","TEAM_LEAD"),is_active=True).values_list("id",flat=True))
        if valid_ids != set(str(x) for x in ids): return Response({"detail":"Every recruiter must be an active HR or Team Lead user."},status=400)
        for rid in ids:
            obj,was_created=JobAssignment.objects.get_or_create(job=job,recruiter_id=rid,defaults={"assigned_by":request.user,"is_active":True})
            if not was_created and not obj.is_active: obj.is_active=True; obj.assigned_by=request.user; obj.save()
            created.append(str(obj.id))
        return Response({"assignment_ids":created})
    @action(detail=True,methods=["post"])
    def match(self,request,pk=None):
        job=self.get_object(); run=run_matching(job,request.user)
        return Response({"match_run_id":str(run.id),"candidates_processed":run.candidates_processed,"results":[{"candidate":str(r.candidate_id),"candidate_code":r.candidate.candidate_code,"name":r.candidate.full_name,"score":float(r.overall_score),"missing_mandatory_skills":r.missing_mandatory_skills} for r in run.results.select_related("candidate").order_by("-overall_score")[:100]]})
