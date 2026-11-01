import uuid

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        MANAGEMENT = "MANAGEMENT", "Management"
        SALES = "SALES", "Sales Executive"
        HR = "HR", "HR Executive"
        TEAM_LEAD = "TEAM_LEAD", "Team Lead"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee_code = models.CharField(max_length=30, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.HR)
    phone = models.CharField(max_length=25, blank=True)
    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    date_joined_company = models.DateField(null=True, blank=True)
    objects = UserManager()

    def __str__(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        raw = kwargs.get("raw", False)
        super().save(*args, **kwargs)
        if not raw:
            self.sync_role_group()

    def sync_role_group(self):
        """Keep the role's default group, without removing any other groups."""
        from django.contrib.auth.models import Group

        from apps.access import ROLE_TO_GROUP

        group_name = ROLE_TO_GROUP.get(self.role)
        if not group_name:
            return
        role_group_names = list(ROLE_TO_GROUP.values())
        existing = list(Group.objects.filter(name__in=role_group_names))
        if not any(group.name == group_name for group in existing):
            return
        self.groups.remove(*existing)
        self.groups.add(Group.objects.get(name=group_name))
