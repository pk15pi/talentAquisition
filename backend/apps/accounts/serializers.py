from rest_framework import serializers
from .models import User
class UserSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True,required=False,min_length=10)
    can_own_client=serializers.SerializerMethodField()
    can_be_assigned_recruiter=serializers.SerializerMethodField()
    class Meta:
        model=User
        fields=(
            "id","username","email","first_name","last_name","employee_code","role","phone","is_active","password",
            "can_own_client","can_be_assigned_recruiter",
        )
        read_only_fields=("id","can_own_client","can_be_assigned_recruiter")
    def get_can_own_client(self,obj):
        return obj.has_perm("clients.own_client")
    def get_can_be_assigned_recruiter(self,obj):
        return obj.has_perm("jobs.be_assigned_recruiter")
    def create(self,validated_data):
        password=validated_data.pop("password",None)
        user=User(**validated_data)
        if password: user.set_password(password)
        else: user.set_unusable_password()
        user.save()
        user.assign_default_role_group()
        return user
    def update(self,instance,validated_data):
        password=validated_data.pop("password",None)
        for key,value in validated_data.items(): setattr(instance,key,value)
        if password: instance.set_password(password)
        instance.save(); return instance
