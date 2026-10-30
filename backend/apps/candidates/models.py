import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
class Candidate(models.Model):
    class Source(models.TextChoices): LINKEDIN="LINKEDIN","LinkedIn"; REFERRAL="REFERRAL","Referral"; JOB_PORTAL="JOB_PORTAL","Job Portal"; WEBSITE="WEBSITE","Website"; INTERNAL="INTERNAL","Internal"; OTHER="OTHER","Other"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    candidate_code=models.CharField(max_length=30,unique=True,blank=True)
    full_name=models.CharField(max_length=200); email=models.EmailField(blank=True); normalized_email=models.CharField(max_length=254,blank=True)
    phone=models.CharField(max_length=25,blank=True); normalized_phone=models.CharField(max_length=25,blank=True)
    current_company=models.CharField(max_length=200,blank=True); total_experience=models.DecimalField(max_digits=4,decimal_places=1,null=True,blank=True)
    current_ctc=models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True); expected_ctc=models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    location=models.CharField(max_length=150,blank=True); notice_period_days=models.PositiveIntegerField(null=True,blank=True)
    source=models.CharField(max_length=20,choices=Source.choices,default=Source.OTHER)
    sourced_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="sourced_candidates")
    is_active=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: indexes=[models.Index(fields=["normalized_email"]),models.Index(fields=["normalized_phone"]),models.Index(fields=["location"])]
    def save(self,*args,**kwargs):
        self.normalized_email=(self.email or "").strip().lower(); self.normalized_phone="".join(c for c in (self.phone or "") if c.isdigit())
        if not self.candidate_code:
            from apps.organizations.utils import next_business_code
            self.candidate_code=next_business_code("candidate","SW-CAN-",5)
        super().save(*args,**kwargs)
    def __str__(self): return f"{self.candidate_code} - {self.full_name}"
class Resume(models.Model):
    candidate=models.ForeignKey(Candidate,on_delete=models.CASCADE,related_name="resumes")
    file=models.FileField(upload_to="resumes/%Y/%m/"); original_filename=models.CharField(max_length=255); file_hash=models.CharField(max_length=64,blank=True)
    parsed_text=models.TextField(blank=True); parsing_status=models.CharField(max_length=20,choices=[("PENDING","Pending"),("PROCESSING","Processing"),("COMPLETED","Completed"),("FAILED","Failed")],default="PENDING")
    version=models.PositiveIntegerField(default=1); is_primary=models.BooleanField(default=False)
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); uploaded_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["candidate","version"],name="unique_candidate_resume_version"),models.UniqueConstraint(fields=["candidate"],condition=Q(is_primary=True),name="one_primary_resume_per_candidate")]
class CandidateNote(models.Model):
    candidate=models.ForeignKey(Candidate,on_delete=models.CASCADE,related_name="notes"); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    note=models.TextField(); created_at=models.DateTimeField(auto_now_add=True)
class CandidateConsent(models.Model):
    candidate=models.ForeignKey(Candidate,on_delete=models.CASCADE,related_name="consents")
    purpose=models.CharField(max_length=150); source=models.CharField(max_length=150,blank=True); processing_basis=models.CharField(max_length=100)
    recorded_at=models.DateTimeField(auto_now_add=True); expires_at=models.DateTimeField(null=True,blank=True); withdrawn_at=models.DateTimeField(null=True,blank=True)
