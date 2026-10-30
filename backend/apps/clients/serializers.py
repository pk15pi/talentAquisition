from rest_framework import serializers
from .models import Client, ClientContact, ClientActivity
class ClientContactSerializer(serializers.ModelSerializer):
    class Meta: model=ClientContact; fields="__all__"; read_only_fields=("id","created_at")
class ClientActivitySerializer(serializers.ModelSerializer):
    class Meta: model=ClientActivity; fields="__all__"; read_only_fields=("user","created_at")
class ClientSerializer(serializers.ModelSerializer):
    contacts=ClientContactSerializer(many=True,read_only=True)
    class Meta:
        model=Client; fields="__all__"; read_only_fields=("id","client_code","created_by","created_at","updated_at")
        extra_kwargs={"sales_owner":{"required":False}}
