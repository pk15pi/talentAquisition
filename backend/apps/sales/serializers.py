from rest_framework import serializers

from .models import SalesOpportunity


class SalesOpportunitySerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = SalesOpportunity
        fields = (
            "id",
            "client",
            "client_name",
            "owner",
            "owner_name",
            "title",
            "stage",
            "expected_value",
            "next_follow_up",
            "notes",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"owner": {"required": False}}
        read_only_fields = ("client_name", "owner_name", "created_at", "updated_at")

    def get_client_name(self, obj):
        return obj.client.company_name if obj.client_id else ""

    def get_owner_name(self, obj):
        if not obj.owner_id:
            return ""
        return obj.owner.get_full_name() or obj.owner.username
