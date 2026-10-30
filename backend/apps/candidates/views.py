import hashlib
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser,FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Candidate,Resume,CandidateNote
from .serializers import CandidateSerializer,ResumeSerializer,CandidateNoteSerializer
from apps.common import RolePermission
class CandidateViewSet(viewsets.ModelViewSet):
    queryset=Candidate.objects.prefetch_related("resumes","candidate_skills__skill").all().order_by("-created_at")
    serializer_class=CandidateSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","HR","TEAM_LEAD")
    def perform_create(self,serializer): serializer.save(sourced_by=self.request.user)
    def get_queryset(self):
        qs=super().get_queryset(); q=self.request.query_params.get("q")
        if q: qs=qs.filter(full_name__icontains=q) | qs.filter(email__icontains=q) | qs.filter(location__icontains=q) | qs.filter(candidate_skills__skill__name__icontains=q)
        return qs.distinct()
    @action(detail=True,methods=["post"],parser_classes=[MultiPartParser,FormParser],url_path="upload-resume")
    def upload_resume(self,request,pk=None):
        candidate=self.get_object(); file=request.FILES.get("file")
        if not file: return Response({"detail":"file is required"},status=400)
        if file.size>10*1024*1024: return Response({"detail":"Maximum file size is 10 MB"},status=400)
        ext=file.name.lower().rsplit(".",1)[-1] if "." in file.name else ""
        if ext not in {"pdf","docx"}: return Response({"detail":"Only PDF and DOCX files are supported"},status=400)
        digest=hashlib.sha256(file.read()).hexdigest(); file.seek(0)
        version=(candidate.resumes.order_by("-version").values_list("version",flat=True).first() or 0)+1
        resume=Resume.objects.create(candidate=candidate,file=file,original_filename=file.name,file_hash=digest,version=version,is_primary=not candidate.resumes.filter(is_primary=True).exists(),uploaded_by=request.user)
        from .tasks import parse_resume
        parse_resume.delay(resume.id)
        return Response(ResumeSerializer(resume).data,status=201)
class CandidateNoteViewSet(viewsets.ModelViewSet):
    queryset=CandidateNote.objects.all(); serializer_class=CandidateNoteSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","HR","TEAM_LEAD")
    def perform_create(self,serializer): serializer.save(user=self.request.user)
