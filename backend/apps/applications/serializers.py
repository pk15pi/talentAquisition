from rest_framework import serializers
from .models import Application,ApplicationHistory
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model=Application; fields="__all__"; read_only_fields=("id","application_code","created_at","updated_at")
        extra_kwargs={"recruiter":{"required":False}}
class ApplicationHistorySerializer(serializers.ModelSerializer):
    class Meta: model=ApplicationHistory; fields="__all__"
