from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from .models import Placement

FINANCIAL_FIELDS = (
    "offered_ctc",
    "agreed_fee_type",
    "agreed_fee_value",
    "expected_revenue",
    "guarantee_period_days",
)


def derive_expected_revenue(fee_type, fee_value, offered_ctc):
    if fee_type == "PERCENTAGE" and fee_value is not None and offered_ctc is not None:
        return (Decimal(offered_ctc) * Decimal(fee_value) / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    if fee_type == "FIXED" and fee_value is not None:
        return Decimal(fee_value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return None


class PlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Placement
        fields = "__all__"
        extra_kwargs = {
            "agreed_fee_type": {"required": False},
            "agreed_fee_value": {"required": False},
            "expected_revenue": {"required": False},
            "guarantee_period_days": {"required": False},
        }

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def _can_view_financials(self):
        user = self._user()
        return bool(user and user.is_authenticated and user.has_perm("placements.view_placement_financials"))

    def _can_change_financials(self):
        user = self._user()
        return bool(user and user.is_authenticated and user.has_perm("placements.change_placement_financials"))

    def _apply_commercial_terms(self, attrs):
        application = attrs.get("application") or getattr(self.instance, "application", None)
        if application is None:
            return
        terms = application.job.effective_commercial_terms()
        if self.instance is None:
            if "agreed_fee_type" not in attrs and terms["fee_type"]:
                attrs["agreed_fee_type"] = terms["fee_type"]
            if "agreed_fee_value" not in attrs and terms["fee_value"] is not None:
                attrs["agreed_fee_value"] = terms["fee_value"]
            if "guarantee_period_days" not in attrs and terms["guarantee_period_days"] is not None:
                attrs["guarantee_period_days"] = terms["guarantee_period_days"]
        if "expected_revenue" in attrs:
            return
        if self.instance is None or any(
            key in attrs for key in ("offered_ctc", "agreed_fee_type", "agreed_fee_value")
        ):
            fee_type = attrs.get("agreed_fee_type", getattr(self.instance, "agreed_fee_type", None))
            fee_value = attrs.get("agreed_fee_value", getattr(self.instance, "agreed_fee_value", None))
            offered_ctc = attrs.get("offered_ctc", getattr(self.instance, "offered_ctc", None))
            revenue = derive_expected_revenue(fee_type, fee_value, offered_ctc)
            if revenue is not None:
                attrs["expected_revenue"] = revenue

    def validate(self, attrs):
        self._apply_commercial_terms(attrs)
        if self.instance is None:
            missing = [
                name
                for name in ("offered_ctc", "agreed_fee_type", "agreed_fee_value", "expected_revenue")
                if attrs.get(name) in (None, "")
            ]
            if missing:
                raise serializers.ValidationError(
                    "Placement fee terms are missing. Set them here or on the client or job description. "
                    f"Still required: {', '.join(missing)}."
                )
        if set(attrs) & set(FINANCIAL_FIELDS) and not self._can_change_financials():
            raise serializers.ValidationError("You do not have permission to set placement commercial fields.")
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self._can_view_financials():
            for field in FINANCIAL_FIELDS:
                data.pop(field, None)
        return data
