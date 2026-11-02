"""Report queries.

Client counts use the first ``ClientOwnershipHistory`` row (the owner at
creation). A later owner change does not move that credit. Invoices, when
the caller may see financial figures, use the owner whose history interval
contains ``invoice.created_at``.

Job descriptions have no sales-owner history table. JD counts stay on the
current ``sales_owner``. Application recruiter is the recruiter stored on
the application; the API does not rewrite it.

HR output has no fee, revenue, or invoice figures.
"""

from collections import defaultdict
from datetime import datetime, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.utils import timezone

from apps.access import user_has
from apps.applications.models import Application
from apps.billing.models import Invoice, Payment
from apps.candidates.models import Candidate
from apps.clients.models import Client, ClientOwnershipHistory
from apps.jobs.models import Job
from apps.placements.models import Placement

User = get_user_model()


def _bounds(date_from, date_to):
    start = end = None
    zone = timezone.get_current_timezone()
    if date_from is not None:
        start = timezone.make_aware(datetime.combine(date_from, time.min), zone)
    if date_to is not None:
        end = timezone.make_aware(datetime.combine(date_to, time.max), zone)
    return start, end


def _apply_created(queryset, start, end):
    if start is not None:
        queryset = queryset.filter(created_at__gte=start)
    if end is not None:
        queryset = queryset.filter(created_at__lte=end)
    return queryset


def _users(ids):
    return {user.pk: user for user in User.objects.filter(pk__in=ids)}


def _person(user):
    if user is None:
        return {"id": None, "first_name": "", "last_name": ""}
    return {"id": user.pk, "first_name": user.first_name, "last_name": user.last_name}


def creation_owner_map(client_ids):
    owners = {}
    rows = (
        ClientOwnershipHistory.objects.filter(client_id__in=client_ids)
        .order_by("changed_at")
        .values_list("client_id", "new_owner_id")
    )
    for client_id, owner_id in rows:
        owners.setdefault(client_id, owner_id)
    return owners


def history_by_client(client_ids):
    grouped = defaultdict(list)
    rows = (
        ClientOwnershipHistory.objects.filter(client_id__in=client_ids)
        .order_by("changed_at")
        .values_list("client_id", "changed_at", "new_owner_id")
    )
    for client_id, changed_at, owner_id in rows:
        grouped[client_id].append((changed_at, owner_id))
    return grouped


def owner_at(client_id, moment, fallback, history):
    chosen = None
    for changed_at, owner_id in history.get(client_id, ()):
        if changed_at <= moment:
            chosen = owner_id
        else:
            break
    return chosen or fallback


def clients_for_report(user):
    """Clients the user may include in a report.

    Callers who can see every client get the full table. Everyone else gets
    clients they own now and clients they appear on in ownership history, so
    a transferred client can still be credited to the earlier owner.
    """
    queryset = Client.objects.all()
    if user_has(user, "clients.view_all_clients"):
        return queryset
    history_ids = ClientOwnershipHistory.objects.filter(Q(new_owner=user) | Q(old_owner=user)).values("client_id")
    return queryset.filter(Q(sales_owner=user) | Q(pk__in=history_ids))


def _department_ok(user, department_id):
    if department_id is None:
        return True
    return bool(user and user.department_id == department_id)


def overview(user, filters):
    start, end = _bounds(filters.get("date_from"), filters.get("date_to"))
    clients = clients_for_report(user)
    jobs = Job.objects.all()
    if not user_has(user, "jobs.view_all_jobs"):
        jobs = jobs.filter(sales_owner=user)
    status = filters.get("status")
    if status in Job.Status.values:
        jobs = jobs.filter(status=status)
    else:
        jobs = jobs.filter(status=Job.Status.OPEN)
    if status in Client.Status.values:
        clients = clients.filter(status=status)
    if filters.get("client"):
        clients = clients.filter(pk=filters["client"])
        jobs = jobs.filter(client_id=filters["client"])
    if filters.get("job"):
        jobs = jobs.filter(pk=filters["job"])
    clients = _apply_created(clients, start, end)
    jobs = _apply_created(jobs, start, end)

    client_rows = list(clients)
    created_owners = creation_owner_map([row.pk for row in client_rows])
    people = _users(
        [created_owners.get(row.pk) or row.sales_owner_id for row in client_rows]
        + [row.sales_owner_id for row in jobs]
    )
    employee = filters.get("employee")
    sales_executive = filters.get("sales_executive")
    department = filters.get("department")

    def client_kept(row):
        owner_id = created_owners.get(row.pk) or row.sales_owner_id
        owner = people.get(owner_id)
        if not user_has(user, "clients.view_all_clients") and owner_id != user.pk:
            return False
        if employee and owner_id != employee:
            return False
        if sales_executive and owner_id != sales_executive:
            return False
        return _department_ok(owner, department)

    def job_kept(row):
        owner = people.get(row.sales_owner_id)
        if employee and row.sales_owner_id != employee:
            return False
        if sales_executive and row.sales_owner_id != sales_executive:
            return False
        return _department_ok(owner, department)

    client_count = sum(1 for row in client_rows if client_kept(row))
    job_count = sum(1 for row in jobs if job_kept(row))

    if user_has(user, "candidates.view_candidate"):
        candidates = Candidate.objects.filter(is_active=True)
    else:
        candidates = Candidate.objects.none()
    candidates = _apply_created(candidates, start, end)
    if employee:
        candidates = candidates.filter(sourced_by_id=employee)
    if department:
        candidates = candidates.filter(sourced_by__department_id=department)

    applications = Application.objects.all()
    placements = Placement.objects.filter(status="JOINED")
    if not user_has(user, "applications.view_all_applications"):
        applications = applications.filter(recruiter=user)
        placements = placements.filter(application__recruiter=user)
    applications = _apply_created(applications, start, end)
    placements = _apply_created(placements, start, end)
    if status in Application.Status.values:
        applications = applications.filter(status=status)
    if filters.get("recruiter"):
        applications = applications.filter(recruiter_id=filters["recruiter"])
        placements = placements.filter(application__recruiter_id=filters["recruiter"])
    if employee:
        applications = applications.filter(recruiter_id=employee)
        placements = placements.filter(application__recruiter_id=employee)
    if department:
        applications = applications.filter(recruiter__department_id=department)
        placements = placements.filter(application__recruiter__department_id=department)
    if filters.get("client"):
        applications = applications.filter(job__client_id=filters["client"])
        placements = placements.filter(application__job__client_id=filters["client"])
    if filters.get("job"):
        applications = applications.filter(job_id=filters["job"])
        placements = placements.filter(application__job_id=filters["job"])

    show_money = user_has(user, "reports.view_financial_report")
    visible_client_ids = clients_for_report(user).values("pk")
    invoices = Invoice.objects.exclude(status="VOID").filter(client_id__in=visible_client_ids)
    payments = Payment.objects.filter(invoice__client_id__in=visible_client_ids)
    invoices = _apply_created(invoices, start, end)
    if start is not None:
        payments = payments.filter(payment_date__gte=start.date())
    if end is not None:
        payments = payments.filter(payment_date__lte=end.date())
    if filters.get("client"):
        invoices = invoices.filter(client_id=filters["client"])
        payments = payments.filter(invoice__client_id=filters["client"])
    return {
        "clients": client_count,
        "open_jobs": job_count,
        "candidates": candidates.count(),
        "applications": applications.count(),
        "joined_placements": placements.count() if user_has(user, "placements.view_placement") or show_money else 0,
        "invoiced_revenue": float(invoices.aggregate(v=Sum("total"))["v"] or 0) if show_money else 0,
        "payments_received": float(payments.aggregate(v=Sum("amount"))["v"] or 0) if show_money else 0,
        "attribution": {
            "clients": "owner_at_creation",
            "jobs": "current_sales_owner",
        },
    }


def hr_report(user, filters):
    start, end = _bounds(filters.get("date_from"), filters.get("date_to"))
    applications = Application.objects.all()
    candidates = Candidate.objects.all()
    if not user_has(user, "applications.view_all_applications"):
        applications = applications.filter(recruiter=user)
    if not user_has(user, "candidates.view_candidate"):
        candidates = Candidate.objects.none()
    elif not user_has(user, "applications.view_all_applications"):
        candidates = candidates.filter(sourced_by=user)
    applications = _apply_created(applications, start, end)
    candidates = _apply_created(candidates, start, end)
    status = filters.get("status")
    if status in Application.Status.values:
        applications = applications.filter(status=status)
    recruiter = filters.get("recruiter") or filters.get("employee")
    if recruiter:
        applications = applications.filter(recruiter_id=recruiter)
    if filters.get("employee"):
        candidates = candidates.filter(sourced_by_id=filters["employee"])
    if filters.get("department"):
        applications = applications.filter(recruiter__department_id=filters["department"])
        candidates = candidates.filter(sourced_by__department_id=filters["department"])
    if filters.get("client"):
        applications = applications.filter(job__client_id=filters["client"])
    if filters.get("job"):
        applications = applications.filter(job_id=filters["job"])
    if filters.get("sales_executive"):
        applications = applications.filter(job__sales_owner_id=filters["sales_executive"])
    rows = applications.values("recruiter__id", "recruiter__first_name", "recruiter__last_name")
    from django.db.models import Count

    return {
        "applications_by_recruiter": list(rows.annotate(applications=Count("id"))),
        "candidates_sourced_by": list(
            candidates.values("sourced_by__id", "sourced_by__first_name", "sourced_by__last_name").annotate(
                candidates_sourced=Count("id")
            )
        ),
        "attribution": {"applications": "application_recruiter", "candidates": "sourced_by"},
    }


def _group_counts(pairs, prefix, count_name):
    totals = defaultdict(int)
    for owner_id, amount in pairs:
        totals[owner_id] += amount
    people = _users([key for key in totals if key is not None])
    rows = []
    for owner_id, count in totals.items():
        person = _person(people.get(owner_id))
        rows.append(
            {
                f"{prefix}__id": person["id"],
                f"{prefix}__first_name": person["first_name"],
                f"{prefix}__last_name": person["last_name"],
                count_name: count,
            }
        )
    return rows


def sales_report(user, filters):
    start, end = _bounds(filters.get("date_from"), filters.get("date_to"))
    jobs = Job.objects.all()
    clients = clients_for_report(user)
    if not user_has(user, "jobs.view_all_jobs"):
        jobs = jobs.filter(sales_owner=user)
    status = filters.get("status")
    if status in Job.Status.values:
        jobs = jobs.filter(status=status)
    if status in Client.Status.values:
        clients = clients.filter(status=status)
    if filters.get("client"):
        clients = clients.filter(pk=filters["client"])
        jobs = jobs.filter(client_id=filters["client"])
    if filters.get("job"):
        jobs = jobs.filter(pk=filters["job"])
    clients = list(_apply_created(clients, start, end))
    jobs = list(_apply_created(jobs, start, end))
    created_owners = creation_owner_map([row.pk for row in clients])
    owner_ids = [created_owners.get(row.pk) or row.sales_owner_id for row in clients]
    owner_ids += [row.sales_owner_id for row in jobs]
    people = _users(owner_ids)
    employee = filters.get("employee")
    sales_executive = filters.get("sales_executive")
    department = filters.get("department")

    def keep(owner_id, *, restrict_to_self):
        if restrict_to_self and owner_id != user.pk:
            return False
        if employee and owner_id != employee:
            return False
        if sales_executive and owner_id != sales_executive:
            return False
        return _department_ok(people.get(owner_id), department)

    see_all_clients = user_has(user, "clients.view_all_clients")
    see_all_jobs = user_has(user, "jobs.view_all_jobs")
    client_pairs = []
    for row in clients:
        owner_id = created_owners.get(row.pk) or row.sales_owner_id
        if keep(owner_id, restrict_to_self=not see_all_clients):
            client_pairs.append((owner_id, 1))
    job_pairs = [
        (row.sales_owner_id, 1) for row in jobs if keep(row.sales_owner_id, restrict_to_self=not see_all_jobs)
    ]
    payload = {
        "jds_by_sales_owner": _group_counts(job_pairs, "sales_owner", "jds"),
        "clients_by_sales_owner": _group_counts(client_pairs, "sales_owner", "clients"),
        "attribution": {
            "clients": "owner_at_creation",
            "jobs": "current_sales_owner",
            "jobs_note": "Job sales-owner changes are not stored in a history table.",
        },
    }
    if user_has(user, "reports.view_financial_report"):
        visible_clients = clients_for_report(user).values("pk")
        invoices = list(
            _apply_created(
                Invoice.objects.exclude(status="VOID").filter(client_id__in=visible_clients).select_related("client"),
                start,
                end,
            )
        )
        if filters.get("client"):
            invoices = [row for row in invoices if row.client_id == filters["client"]]
        history = history_by_client([row.client_id for row in invoices])
        money = defaultdict(lambda: Decimal("0.00"))
        for invoice in invoices:
            owner_id = owner_at(invoice.client_id, invoice.created_at, invoice.client.sales_owner_id, history)
            if keep(owner_id, restrict_to_self=not see_all_clients):
                money[owner_id] += invoice.total
        people.update(_users(money.keys()))
        payload["invoiced_by_owner"] = []
        for owner_id, total in money.items():
            person = _person(people.get(owner_id))
            payload["invoiced_by_owner"].append(
                {
                    "sales_owner__id": person["id"],
                    "sales_owner__first_name": person["first_name"],
                    "sales_owner__last_name": person["last_name"],
                    "invoiced_total": str(total),
                }
            )
    return payload
