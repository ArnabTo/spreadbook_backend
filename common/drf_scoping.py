from __future__ import annotations

from typing import Optional, Set, Sequence

from django.db.models import Q, QuerySet


def is_unrestricted_user(user) -> bool:
    return (
        bool(getattr(user, "is_superuser", False))
        or getattr(user, "role", None) == "software_owner"
    )


def get_company_ids_for_user(user) -> Set[str]:
    company_ids: Set[str] = set()

    if getattr(user, "companyId_id", None):
        company_ids.add(str(user.companyId_id))
        return company_ids

    if hasattr(user, "branchAccess"):
        company_ids.update(
            str(cid) for cid in user.branchAccess.values_list("company_id", flat=True)
        )

    return company_ids


def get_allowed_branch_ids_for_user(user) -> Optional[Set[str]]:
    """Returns None for unrestricted/no-explicit-branch-access (treat as company-wide).

    Returns a set of branch IDs when the user has explicit branch assignments.
    """

    if is_unrestricted_user(user):
        return None

    if not hasattr(user, "branchAccess"):
        return None

    if user.branchAccess.exists():
        return set(str(bid) for bid in user.branchAccess.values_list("id", flat=True))

    return None


def apply_company_branch_scope(
    *,
    request,
    queryset: QuerySet,
    company_id_field: Optional[str],
    branch_id_field: Optional[str],
    branch_param_names: Sequence[str] = ("branch_id", "branchId"),
) -> QuerySet:
    """Apply company + optional branch scoping based on request.user.

    - Company scoping is always applied when company_id_field is provided.
    - Branch scoping is applied only when the user has explicit branchAccess.
      If a branch query param is provided, it is validated against branchAccess.
    """

    user = request.user
    if is_unrestricted_user(user):
        return queryset

    # Company scope
    company_ids = get_company_ids_for_user(user)
    if company_id_field:
        if not company_ids:
            return queryset.none()
        queryset = queryset.filter(**{f"{company_id_field}__in": list(company_ids)})

    # Branch scope (only if explicit access exists)
    allowed_branch_ids = get_allowed_branch_ids_for_user(user)
    if branch_id_field and allowed_branch_ids is not None:
        requested_branch_id = None
        for name in branch_param_names:
            if name in request.query_params and request.query_params.get(name):
                requested_branch_id = request.query_params.get(name)
                break

        if requested_branch_id:
            if requested_branch_id not in allowed_branch_ids:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("You do not have access to this branch")
            queryset = queryset.filter(**{branch_id_field: requested_branch_id})
        else:
            queryset = queryset.filter(
                Q(**{f"{branch_id_field}__in": list(allowed_branch_ids)})
                | Q(**{f"{branch_id_field}__isnull": True})
            )

    return queryset.distinct()
