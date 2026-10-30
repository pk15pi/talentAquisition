from rest_framework import serializers

from .models import Placement

FINANCIAL_FIELDS = (
    "offered_ctc",
    "agreed_fee_type",
    "agreed_fee_value",
    "expected_revenue",
    "guarantee_period_days",
)


class PlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Placement
        fields = "__all__"

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def _can_view_financials(self):
        user = self._user()
        return bool(user and user.is_authenticated and user.has_perm("placements.view_placement_financials"))

    def _can_change_financials(self):
        user = self._user()
        return bool(user and user.is_authenticated and user.has_perm("placements.change_placement_financials"))

    def validate(self, attrs):
        if set(attrs) & set(FINANCIAL_FIELDS) and not self._can_change_financials():
            raise serializers.ValidationError("You do not have permission to set placement commercial fields.")
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self._can_view_financials():
            for field in FINANCIAL_FIELDS:
                data.pop(field, None)
        return data
