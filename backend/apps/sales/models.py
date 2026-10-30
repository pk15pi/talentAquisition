import uuid
from django.conf import settings
from django.db import models
class SalesOpportunity(models.Model):
    class Stage(models.TextChoices): NEW="NEW","New"; CONTACTED="CONTACTED","Contacted"; QUALIFIED="QUALIFIED","Qualified"; PROPOSAL="PROPOSAL","Proposal"; WON="WON","Won"; LOST="LOST","Lost"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    client=models.ForeignKey("clients.Client",on_delete=models.PROTECT,related_name="opportunities")
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="sales_opportunities")
    title=models.CharField(max_length=200); stage=models.CharField(max_length=20,choices=Stage.choices,default=Stage.NEW)
    expected_value=models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    next_follow_up=models.DateTimeField(null=True,blank=True); notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
