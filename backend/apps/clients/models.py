import uuid
from django.conf import settings
from django.db import models
class Client(models.Model):
    class Status(models.TextChoices): LEAD="LEAD","Lead"; ACTIVE="ACTIVE","Active"; INACTIVE="INACTIVE","Inactive"; BLACKLISTED="BLACKLISTED","Blacklisted"
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_code=models.CharField(max_length=30, unique=True, blank=True)
    company_name=models.CharField(max_length=255)
    industry=models.CharField(max_length=100, blank=True); website=models.URLField(blank=True); address=models.TextField(blank=True)
    sales_owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="owned_clients")
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.LEAD)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="created_clients")
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def save(self,*args,**kwargs):
        if not self.client_code:
            from apps.organizations.utils import next_business_code
            self.client_code=next_business_code("client","SW-CLI-",4)
        super().save(*args,**kwargs)
    def __str__(self): return f"{self.client_code} - {self.company_name}"
class ClientContact(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    client=models.ForeignKey(Client,on_delete=models.CASCADE,related_name="contacts")
    name=models.CharField(max_length=150); designation=models.CharField(max_length=100,blank=True); email=models.EmailField(blank=True); phone=models.CharField(max_length=25,blank=True); is_primary=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
class ClientOwnershipHistory(models.Model):
    client=models.ForeignKey(Client,on_delete=models.CASCADE,related_name="ownership_history")
    old_owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="client_ownership_from",null=True,blank=True)
    new_owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="client_ownership_to")
    changed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    changed_at=models.DateTimeField(auto_now_add=True); remarks=models.TextField(blank=True)

class ClientActivity(models.Model):
    client=models.ForeignKey(Client,on_delete=models.CASCADE,related_name="activities")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    activity_type=models.CharField(max_length=40,choices=[("CALL","Call"),("EMAIL","Email"),("MEETING","Meeting"),("NOTE","Note"),("FOLLOW_UP","Follow-up")],default="NOTE")
    subject=models.CharField(max_length=200,blank=True); notes=models.TextField(blank=True); follow_up_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
