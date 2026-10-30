from django.db import models


class ReportAccess(models.Model):
    """Empty anchor so report visibility is a Django permission, not a role string."""

    class Meta:
        default_permissions = ()
        permissions = [
            ("view_overview_report", "Can view the overview report"),
            ("view_hr_report", "Can view the HR productivity report"),
            ("view_sales_report", "Can view the sales productivity report"),
            ("view_financial_report", "Can view financial figures on reports"),
        ]
        verbose_name = "report access"
