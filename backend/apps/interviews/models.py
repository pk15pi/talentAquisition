from django.conf import settings
from django.db import models
class Interview(models.Model):
    application=models.ForeignKey("applications.Application",on_delete=models.PROTECT,related_name="interviews")
    round_name=models.CharField(max_length=100); interview_date=models.DateTimeField(); interviewer_name=models.CharField(max_length=150,blank=True)
    feedback=models.TextField(blank=True); result=models.CharField(max_length=20,choices=[("PENDING","Pending"),("PASSED","Passed"),("FAILED","Failed"),("ON_HOLD","On Hold")],default="PENDING")
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
