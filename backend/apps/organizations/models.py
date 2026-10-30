import uuid
from django.db import models
class Department(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name=models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class CodeSequence(models.Model):
    key=models.CharField(max_length=80,unique=True)
    current_value=models.PositiveBigIntegerField(default=0)
