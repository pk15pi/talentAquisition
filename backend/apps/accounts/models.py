import uuid

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def _create_user(self, username, email, password, **extra_fields):
        user = super()._create_user(username, email, password, **extra_fields)
        user.assign_default_role_group()
        return user

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
        super().save(*args, **kwargs)

    def assign_default_role_group(self):
        """Add the group for this role. Never removes a membership.

        Call this only when provisioning a user (``create_user``,
        ``create_superuser``, the admin add form, or the user API create).
        Ordinary saves and logins must not call it.
        """
        from django.contrib.auth.models import Group

        from apps.access import ROLE_TO_GROUP

        group_name = ROLE_TO_GROUP.get(self.role)
        if not group_name:
            return
        group = Group.objects.filter(name=group_name).first()
        if group is not None:
            self.groups.add(group)

    def sync_role_group(self):
        """Backward-compatible name. Adds the role group and removes nothing."""
        self.assign_default_role_group()
