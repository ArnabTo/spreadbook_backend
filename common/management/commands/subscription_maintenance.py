import os
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from authenticator.models import User
from company.models import Company
from common.models import Notification


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def _env_csv_ints(name: str, default: list[int]) -> list[int]:
    raw = os.getenv(name)
    if not raw:
        return default
    out: list[int] = []
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out or default


def _add_months(dt: timezone.datetime, months: int) -> timezone.datetime:
    # Month arithmetic without external deps.
    year = dt.year
    month = dt.month + months
    while month > 12:
        year += 1
        month -= 12
    while month < 1:
        year -= 1
        month += 12

    # Clamp day-of-month
    from calendar import monthrange

    last_day = monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day)


def _next_billing_date(
    now_dt: timezone.datetime, payment_type: str | None
) -> timezone.datetime:
    pt = (payment_type or "monthly").lower()
    if pt == "yearly":
        return _add_months(now_dt, 12)
    if pt == "quarterly":
        return _add_months(now_dt, 3)
    # default monthly
    return _add_months(now_dt, 1)


def _notify_company_admins(
    company: Company,
    *,
    notif_type: str,
    title: str,
    message: str,
    priority: str,
    action_url: str | None = None,
    action_label: str | None = None,
    dedupe_key: str | None = None,
):
    admins = User.objects.filter(
        companyId=company,
        is_active=True,
        role__in=["admin", "super_admin", "manager"],
    ).only("id")

    # If no admins found, still notify any active company users to avoid missing alerts.
    if not admins.exists():
        admins = User.objects.filter(companyId=company, is_active=True).only("id")

    for u in admins:
        Notification.objects.get_or_create(
            user=u,
            dedupe_key=dedupe_key,
            defaults={
                "company": company,
                "type": notif_type,
                "title": title,
                "message": message,
                "priority": priority,
                "actionUrl": action_url,
                "actionLabel": action_label,
                "data": {
                    "companyId": company.id,
                    "subscriptionStatus": company.subscriptionStatus,
                    "subscriptionPlan": company.subscriptionPlan,
                },
            },
        )


class Command(BaseCommand):
    help = "Daily subscription lifecycle maintenance (trial, reminders, grace period, lock)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        now_dt = timezone.now()
        today: date = now_dt.date()

        trial_days = _env_int("DJANGO_TRIAL_DAYS", 30)
        grace_days = _env_int("DJANGO_SUBSCRIPTION_GRACE_DAYS", 15)
        notice_days = _env_csv_ints("DJANGO_SUBSCRIPTION_NOTICE_DAYS", [5, 3])

        companies = Company.objects.all().only(
            "id",
            "name",
            "subscriptionPlan",
            "subscriptionStatus",
            "trialEndsAt",
            "nextBillingDate",
            "paymentType",
            "daysOverdue",
        )

        updated = 0
        created_notifs = 0

        for company in companies:
            status = (company.subscriptionStatus or "").lower()

            # Ensure new companies start with a trial.
            if not status:
                company.subscriptionStatus = "trial"
                company.trialEndsAt = now_dt + timezone.timedelta(days=trial_days)
                company.nextBillingDate = company.trialEndsAt
                company.daysOverdue = 0
                status = "trial"
                updated += 1

            # Determine current due date
            due_dt = None
            if status == "trial":
                due_dt = company.trialEndsAt
                if due_dt and not company.nextBillingDate:
                    company.nextBillingDate = due_dt
                    updated += 1
            else:
                due_dt = company.nextBillingDate

            if not due_dt:
                continue

            days_until_due = (due_dt.date() - today).days

            # Pre-due reminders
            if status in {"trial", "active"} and days_until_due in set(notice_days):
                title = (
                    f"Trial ends in {days_until_due} day(s)"
                    if status == "trial"
                    else f"Subscription renews in {days_until_due} day(s)"
                )
                message = (
                    "Please choose a plan and complete payment to avoid interruption."
                    if status == "trial"
                    else "Please ensure your subscription payment is completed to avoid interruption."
                )
                key = f"sub_notice_{status}_{company.id}_{due_dt.date().isoformat()}_{days_until_due}"
                before = Notification.objects.filter(dedupe_key=key).count()
                _notify_company_admins(
                    company,
                    notif_type="warning",
                    title=title,
                    message=message,
                    priority="high",
                    action_url="billing",
                    action_label="Billing",
                    dedupe_key=key,
                )
                after = Notification.objects.filter(dedupe_key=key).count()
                created_notifs += max(0, after - before)

            # Due reached => overdue starts (grace window)
            if status in {"trial", "active"} and now_dt >= due_dt:
                company.subscriptionStatus = "payment_overdue"
                company.daysOverdue = 0
                updated += 1

                key = f"sub_due_{company.id}_{due_dt.date().isoformat()}"
                before = Notification.objects.filter(dedupe_key=key).count()
                _notify_company_admins(
                    company,
                    notif_type="payment",
                    title="Subscription payment due",
                    message=f"Your subscription is due today. You have {grace_days} day(s) grace before account lock.",
                    priority="urgent",
                    action_url="billing",
                    action_label="Pay now",
                    dedupe_key=key,
                )
                after = Notification.objects.filter(dedupe_key=key).count()
                created_notifs += max(0, after - before)

                status = "payment_overdue"

            # Overdue handling + lock
            if status == "payment_overdue":
                days_over = max(0, (today - due_dt.date()).days)
                if company.daysOverdue != days_over:
                    company.daysOverdue = days_over
                    updated += 1

                if days_over >= grace_days:
                    company.subscriptionStatus = "suspended"
                    updated += 1

                    key = f"sub_locked_{company.id}_{due_dt.date().isoformat()}"
                    before = Notification.objects.filter(dedupe_key=key).count()
                    _notify_company_admins(
                        company,
                        notif_type="error",
                        title="Account locked due to unpaid subscription",
                        message="Your grace period has ended. Please pay to reactivate access.",
                        priority="urgent",
                        action_url="billing",
                        action_label="Pay & Reactivate",
                        dedupe_key=key,
                    )
                    after = Notification.objects.filter(dedupe_key=key).count()
                    created_notifs += max(0, after - before)
                else:
                    # Light reminders during grace
                    if days_over in {7, 14}:
                        key = f"sub_grace_{company.id}_{due_dt.date().isoformat()}_{days_over}"
                        before = Notification.objects.filter(dedupe_key=key).count()
                        _notify_company_admins(
                            company,
                            notif_type="warning",
                            title="Subscription unpaid (grace period)",
                            message=f"Payment is overdue by {days_over} day(s). {grace_days - days_over} day(s) left before lock.",
                            priority="high",
                            action_url="billing",
                            action_label="Pay now",
                            dedupe_key=key,
                        )
                        after = Notification.objects.filter(dedupe_key=key).count()
                        created_notifs += max(0, after - before)

            # If company has no nextBillingDate but is active, set it.
            if (
                company.subscriptionStatus or ""
            ).lower() == "active" and not company.nextBillingDate:
                company.nextBillingDate = _next_billing_date(
                    now_dt, company.paymentType
                )
                updated += 1

            if not dry_run and updated:
                company.save()

        if dry_run:
            transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"subscription_maintenance complete: updated={updated}, notifications_created~={created_notifs}"
            )
        )
