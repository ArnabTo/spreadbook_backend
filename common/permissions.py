import os

from django.utils import timezone

from rest_framework.permissions import BasePermission

from common.drf_scoping import is_unrestricted_user


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


class SubscriptionActivePermission(BasePermission):
    """Optionally enforce company subscription status.

    - Disabled by default.
    - Enable with DJANGO_ENFORCE_SUBSCRIPTION=1
    - Allows software_owner/reseller roles to bypass.

    This is intentionally conservative to avoid breaking existing flows.
    """

    message = "Subscription is not active for this company."

    def has_permission(self, request, view):
        if not _env_bool("DJANGO_ENFORCE_SUBSCRIPTION", default=False):
            return True

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            # Let the normal auth/permission layer decide.
            return True

        role = (getattr(user, "role", "") or "").lower()
        if role in {"software_owner", "reseller"}:
            return True

        company_id = getattr(user, "companyId", None) or getattr(
            user, "company_id", None
        )
        if not company_id:
            # Users without company context (rare) shouldn't be hard-blocked here.
            return True

        grace_days = 15
        try:
            raw_grace = os.getenv("DJANGO_SUBSCRIPTION_GRACE_DAYS")
            if raw_grace:
                grace_days = int(str(raw_grace).strip())
        except Exception:
            grace_days = 15

        # Local import to avoid circular dependencies
        from company.models import Company

        try:
            company = Company.objects.only(
                "subscriptionStatus", "daysOverdue", "nextBillingDate", "trialEndsAt"
            ).get(id=company_id)
        except Company.DoesNotExist:
            return False

        status = (company.subscriptionStatus or "").lower()

        if status in {"active", "trial"}:
            return True

        if status == "payment_overdue":
            # Allow usage during the grace period.
            days_overdue = company.daysOverdue
            if days_overdue is None:
                due = company.nextBillingDate or company.trialEndsAt
                if due:
                    days_overdue = max(0, (timezone.now().date() - due.date()).days)
                else:
                    days_overdue = 0
            return int(days_overdue) < grace_days

        return False


def _user_role(user) -> str:
    return (getattr(user, "role", "") or "").strip().lower()


class RoleRequiredPermission(BasePermission):
    """Base role permission.

    - Always allows unrestricted users (software_owner / superuser).
    - Otherwise requires request.user.role to be in allowed_roles.
    """

    allowed_roles: frozenset[str] = frozenset()
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if is_unrestricted_user(user) or bool(getattr(user, "is_superuser", False)):
            return True
        return _user_role(user) in self.allowed_roles


class IsCompanyAdmin(RoleRequiredPermission):
    """Company admin-ish roles (no cashier/staff)."""

    allowed_roles = frozenset({"super_admin", "admin"})


class IsBranchManagerOrAbove(RoleRequiredPermission):
    """Branch manager + admins + software owner."""

    allowed_roles = frozenset({"manager", "super_admin", "admin", "software_owner"})


class IsPOSOperator(RoleRequiredPermission):
    """Roles allowed to operate POS endpoints."""

    allowed_roles = frozenset(
        {"cashier", "manager", "super_admin", "admin", "software_owner"}
    )
