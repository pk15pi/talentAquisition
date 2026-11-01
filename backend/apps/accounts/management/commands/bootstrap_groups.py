from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.access import (
    GROUP_ADMINISTRATOR,
    GROUP_HR,
    GROUP_MANAGEMENT,
    GROUP_SALES,
    GROUP_TEAM_LEAD,
    HR_PERMS,
    MANAGEMENT_PERMS,
    SALES_PERMS,
    TEAM_LEAD_EXTRA,
)


def _permissions(codes):
    wanted = []
    missing = []
    for code in codes:
        app_label, codename = code.split(".", 1)
        perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
        if perm is None:
            missing.append(code)
        else:
            wanted.append(perm)
    if missing:
        raise RuntimeError("Missing permissions (migrate first): " + ", ".join(missing))
    return wanted


class Command(BaseCommand):
    help = "Create default SynfoTalent groups and their initial permissions. Existing groups are not reset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Replace each default group's permissions with the built-in set. Custom groups are untouched.",
        )

    def handle(self, *args, **options):
        specs = {
            GROUP_ADMINISTRATOR: None,
            GROUP_MANAGEMENT: MANAGEMENT_PERMS,
            GROUP_SALES: SALES_PERMS,
            GROUP_HR: HR_PERMS,
            GROUP_TEAM_LEAD: HR_PERMS + TEAM_LEAD_EXTRA,
        }
        for name, codes in specs.items():
            group, created = Group.objects.get_or_create(name=name)
            if codes is None:
                permissions = list(Permission.objects.all())
            else:
                permissions = _permissions(codes)
            if created or options["reset"]:
                group.permissions.set(permissions)
                action = "reset" if options["reset"] and not created else "created"
                self.stdout.write(f"{action} group {name} with {len(permissions)} permissions")
            else:
                self.stdout.write(f"left existing group {name} unchanged")

        self.stdout.write(self.style.SUCCESS("Groups are ready."))
