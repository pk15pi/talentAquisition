from rest_framework import serializers
from .models import Client, ClientContact, ClientActivity
class ClientContactSerializer(serializers.ModelSerializer):
    class Meta: model=ClientContact; fields="__all__"; read_only_fields=("id","created_at")
class ClientActivitySerializer(serializers.ModelSerializer):
    user_name=serializers.SerializerMethodField()
    class Meta: model=ClientActivity; fields="__all__"; read_only_fields=("user","created_at","user_name")
    def get_user_name(self,obj):
        if not obj.user_id: return ""
        return obj.user.get_full_name() or obj.user.username
class ClientSerializer(serializers.ModelSerializer):
    contacts=ClientContactSerializer(many=True,read_only=True)
    sales_owner_name=serializers.SerializerMethodField()
    class Meta:
        model=Client; fields="__all__"; read_only_fields=("id","client_code","created_by","created_at","updated_at","sales_owner_name")
        extra_kwargs={"sales_owner":{"required":False}}
    def get_sales_owner_name(self,obj):
        if not obj.sales_owner_id: return ""
        return obj.sales_owner.get_full_name() or obj.sales_owner.username
