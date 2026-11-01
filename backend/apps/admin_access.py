"""Shared Django admin guards for SynfoTalent.

Access checks call ``user.has_perm``. Active superusers pass those checks.
Inactive users do not. Deletion of historical and financial rows is refused
in the admin for every account, including superusers: status and ``is_active``
are the supported ways to retire a record.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Q


def perm(user, code: str) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_active and user.has_perm(code))


def users_holding(app_label, codename, extra_ids=()):
    """Active users who hold a permission, plus any rows that must stay selectable."""
    user_model = get_user_model()
    holders = user_model.objects.filter(is_active=True).filter(
        Q(is_superuser=True)
        | Q(
            user_permissions__codename=codename,
            user_permissions__content_type__app_label=app_label,
        )
        | Q(
            groups__permissions__codename=codename,
            groups__permissions__content_type__app_label=app_label,
        )
    )
    if extra_ids:
        return user_model.objects.filter(Q(pk__in=holders.values("pk")) | Q(pk__in=list(extra_ids))).distinct()
    return holders.distinct()


def strip_fieldsets(fieldsets, hidden):
    cleaned = []
    for title, options in fieldsets:
        options = dict(options)
        fields = []
        for field in options.get("fields", ()):
            if isinstance(field, (list, tuple)):
                row = tuple(item for item in field if item not in hidden)
                if row:
                    fields.append(row)
            elif field not in hidden:
                fields.append(field)
        if not fields:
            continue
        options["fields"] = tuple(fields)
        cleaned.append((title, options))
    return cleaned


class SensitiveFieldsMixin:
    """Hide fields unless the user holds the matching view permission.

    Each rule is ``(view_permission, field_names)`` or
    ``(view_permission, field_names, edit_permission)``. A visible field is
    read-only when an edit permission is set and the user does not hold it.
    """

    sensitive_field_rules = ()

    def _sensitive_rules(self):
        for rule in self.sensitive_field_rules:
            if len(rule) == 2:
                view_permission, fields = rule
                edit_permission = None
            else:
                view_permission, fields, edit_permission = rule
            yield view_permission, tuple(fields), edit_permission

    def _hidden_sensitive_fields(self, request):
        hidden = []
        for view_permission, fields, _edit_permission in self._sensitive_rules():
            if not perm(request.user, view_permission):
                hidden.extend(fields)
        return hidden

    def _readonly_sensitive_fields(self, request):
        readonly = []
        hidden = set(self._hidden_sensitive_fields(request))
        for view_permission, fields, edit_permission in self._sensitive_rules():
            if not edit_permission or not perm(request.user, view_permission):
                continue
            if perm(request.user, edit_permission):
                continue
            readonly.extend(field for field in fields if field not in hidden)
        return readonly

    def get_exclude(self, request, obj=None):
        excluded = set(super().get_exclude(request, obj) or ())
        excluded.update(self._hidden_sensitive_fields(request))
        return tuple(excluded) or None

    def get_fields(self, request, obj=None):
        hidden = set(self._hidden_sensitive_fields(request))
        return [field for field in super().get_fields(request, obj) if field not in hidden]

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        readonly.extend(self._readonly_sensitive_fields(request))
        return tuple(dict.fromkeys(readonly))

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        hidden = set(self._hidden_sensitive_fields(request))
        if not hidden:
            return fieldsets
        return strip_fieldsets(fieldsets, hidden)


class NoDeleteMixin:
    """Refuse admin deletion. Callers deactivate or void the row instead."""

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if actions:
            actions.pop("delete_selected", None)
        return actions


class SensitiveModelAdmin(SensitiveFieldsMixin, NoDeleteMixin, admin.ModelAdmin):
    def get_list_display(self, request):
        hidden = set(self._hidden_sensitive_fields(request))
        return tuple(field for field in super().get_list_display(request) if field not in hidden)


class ReadOnlyModelAdmin(NoDeleteMixin, admin.ModelAdmin):
    """History and audit rows. Viewing follows model permissions; nothing is writable."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ParentInlineMixin:
    """Show an inline to people who can view the parent. Edit rights stay explicit."""

    parent_view_permission = ""
    edit_permission = ""
    allow_delete = False

    def has_view_permission(self, request, obj=None):
        if self.parent_view_permission and perm(request.user, self.parent_view_permission):
            return True
        return super().has_view_permission(request, obj)

    def has_add_permission(self, request, obj=None):
        if self.edit_permission:
            return perm(request.user, self.edit_permission)
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if self.edit_permission:
            return perm(request.user, self.edit_permission)
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not self.allow_delete:
            return False
        return super().has_delete_permission(request, obj)


class HistoryInlineMixin(ParentInlineMixin):
    """Append-only history. Admin saves on the parent write these rows."""

    extra = 0
    can_delete = False
    edit_permission = ""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
