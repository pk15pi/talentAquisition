import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
class Job(models.Model):
    class Status(models.TextChoices): DRAFT="DRAFT","Draft"; OPEN="OPEN","Open"; ON_HOLD="ON_HOLD","On Hold"; CLOSED="CLOSED","Closed"; CANCELLED="CANCELLED","Cancelled"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    job_code=models.CharField(max_length=30,unique=True,blank=True)
    client=models.ForeignKey("clients.Client",on_delete=models.PROTECT,related_name="jobs")
    title=models.CharField(max_length=255); jd_text=models.TextField()
    experience_min=models.DecimalField(max_digits=4,decimal_places=1,default=0); experience_max=models.DecimalField(max_digits=4,decimal_places=1,default=0)
    location=models.CharField(max_length=150,blank=True); work_mode=models.CharField(max_length=20,choices=[("OFFICE","Office"),("HYBRID","Hybrid"),("REMOTE","Remote")],default="OFFICE")
    salary_min=models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True); salary_max=models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    positions=models.PositiveIntegerField(default=1); notice_period_days=models.PositiveIntegerField(null=True,blank=True)
    sales_owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="owned_jobs")
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="created_jobs")
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.DRAFT)
    priority=models.CharField(max_length=15,choices=[("LOW","Low"),("MEDIUM","Medium"),("HIGH","High"),("URGENT","Urgent")],default="MEDIUM")
    opened_at=models.DateTimeField(null=True,blank=True); closed_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        indexes=[models.Index(fields=["status","created_at"]),models.Index(fields=["client","status"]),models.Index(fields=["sales_owner","status"])]
        constraints=[models.CheckConstraint(condition=Q(experience_max__gte=models.F("experience_min")),name="job_experience_range_valid"),models.CheckConstraint(condition=Q(salary_max__isnull=True)|Q(salary_min__isnull=True)|Q(salary_max__gte=models.F("salary_min")),name="job_salary_range_valid")]
    def save(self,*args,**kwargs):
        if not self.job_code:
            from apps.organizations.utils import next_business_code
            self.job_code=next_business_code("job","SW-JD-",4)
        super().save(*args,**kwargs)
    def __str__(self): return f"{self.job_code} - {self.title}"
class JobAssignment(models.Model):
    job=models.ForeignKey(Job,on_delete=models.CASCADE,related_name="assignments")
    recruiter=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="job_assignments")
    assigned_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="created_assignments")
    assigned_at=models.DateTimeField(auto_now_add=True); is_active=models.BooleanField(default=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["job","recruiter"],name="unique_job_recruiter_assignment")]
class JobStatusHistory(models.Model):
    job=models.ForeignKey(Job,on_delete=models.CASCADE,related_name="status_history")
    old_status=models.CharField(max_length=20,blank=True); new_status=models.CharField(max_length=20)
    changed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); changed_at=models.DateTimeField(auto_now_add=True); remarks=models.TextField(blank=True)
