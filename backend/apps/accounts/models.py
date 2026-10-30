import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN="ADMIN","Admin"; MANAGEMENT="MANAGEMENT","Management"; SALES="SALES","Sales Executive"; HR="HR","HR Executive"; TEAM_LEAD="TEAM_LEAD","Team Lead"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee_code=models.CharField(max_length=30, unique=True, null=True, blank=True)
    role=models.CharField(max_length=20, choices=Role.choices, default=Role.HR)
    phone=models.CharField(max_length=25, blank=True)
    department=models.ForeignKey("organizations.Department",on_delete=models.SET_NULL,null=True,blank=True,related_name="employees")
    date_joined_company=models.DateField(null=True, blank=True)
    def __str__(self): return self.get_full_name() or self.username
