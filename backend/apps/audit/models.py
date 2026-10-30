from django.conf import settings
from django.db import models
class AuditLog(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    action=models.CharField(max_length=100); entity_type=models.CharField(max_length=100); entity_id=models.CharField(max_length=100,blank=True)
    details=models.JSONField(default=dict,blank=True); ip_address=models.GenericIPAddressField(null=True,blank=True); timestamp=models.DateTimeField(auto_now_add=True)
