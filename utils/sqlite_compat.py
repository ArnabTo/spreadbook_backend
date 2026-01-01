"""utils.sqlite_compat

Historically this project represented `User.branchAccess` as a JSON list (with an
optional sentinel value like "all"). The current codebase uses a ManyToMany
relationship instead.

These helpers are kept for backwards compatibility with call sites and are
implemented to work with BOTH representations.
"""

from django.db import connection


def _normalize_branch_ids(branch_ids):
    if isinstance(branch_ids, (str, int)):
        return [str(branch_ids)]
    return [str(bid) for bid in (branch_ids or [])]


def _user_branch_access_set(user):
    """Return a set of branch identifiers the user can access.

    Supports:
    - ManyToMany: user.branchAccess.values_list('id', flat=True)
    - Legacy list/tuple/set of ids and/or the 'all' sentinel
    """
    branch_access = getattr(user, "branchAccess", None)
    if branch_access is None:
        return set()

    # ManyToMany manager
    if hasattr(branch_access, "values_list"):
        try:
            return set(str(i) for i in branch_access.values_list("id", flat=True))
        except Exception:
            return set()

    if isinstance(branch_access, (list, tuple, set)):
        return set(str(i) for i in branch_access)

    return set()


def filter_users_by_branch_access(queryset, branch_ids, check_active=True):
    """
    Filter users by branch access, compatible with SQLite.

    Args:
        queryset: User queryset to filter
        branch_ids: List of branch IDs to check access for
        check_active: Whether to only include active users

    Returns:
        Filtered queryset or list of users
    """
    if check_active:
        queryset = queryset.filter(is_active=True)

    branch_ids = _normalize_branch_ids(branch_ids)

    # Prefer ORM filtering for ManyToMany (works on SQLite too).
    try:
        numeric_branch_ids = [int(bid) for bid in branch_ids if str(bid).isdigit()]
        if numeric_branch_ids:
            return queryset.filter(branchAccess__id__in=numeric_branch_ids).distinct()
        return queryset.none() if hasattr(queryset, "none") else []
    except Exception:
        # Fall back to python filtering for legacy list-based storage.
        pass

    matching_users = []
    for user in queryset:
        user_access = _user_branch_access_set(user)
        if not user_access:
            continue
        if "all" in user_access or any(bid in user_access for bid in branch_ids):
            matching_users.append(user)
    return matching_users


def check_branch_access_overlap(user_branches, target_branches):
    """
    Check if there's overlap between user branch access and target branches.

    Args:
        user_branches: List of branch IDs user has access to
        target_branches: List of branch IDs to check against

    Returns:
        Boolean indicating if there's overlap
    """
    if not user_branches or not target_branches:
        return False

    # Accept either list-like or ManyToMany managers
    if hasattr(user_branches, "values_list"):
        try:
            user_set = set(str(i) for i in user_branches.values_list("id", flat=True))
        except Exception:
            user_set = set()
    else:
        user_set = set(str(b) for b in user_branches)

    if hasattr(target_branches, "values_list"):
        try:
            target_set = set(
                str(i) for i in target_branches.values_list("id", flat=True)
            )
        except Exception:
            target_set = set()
    else:
        target_set = set(str(b) for b in target_branches)

    # Check for 'all' access
    if "all" in user_set or "all" in target_set:
        return True

    # Check for intersection
    return bool(user_set.intersection(target_set))


def filter_users_by_branch_overlap(queryset, manager_branches, check_active=True):
    """
    Filter users who have overlapping branch access with manager.

    Args:
        queryset: User queryset to filter
        manager_branches: List of branch IDs manager has access to
        check_active: Whether to only include active users

    Returns:
        Filtered queryset or list of users
    """
    if check_active:
        queryset = queryset.filter(is_active=True)

    if not manager_branches:
        return queryset.none() if hasattr(queryset, "none") else []

    if hasattr(manager_branches, "values_list"):
        try:
            manager_branches_set = set(
                str(i) for i in manager_branches.values_list("id", flat=True)
            )
        except Exception:
            manager_branches_set = set()
    else:
        manager_branches_set = set(str(b) for b in manager_branches)

    try:
        # If manager has 'all' access, return all users
        if "all" in manager_branches_set:
            return list(queryset) if "sqlite" in connection.vendor else queryset

        # Prefer ManyToMany ORM filtering
        numeric_branch_ids = [
            int(bid) for bid in manager_branches_set if str(bid).isdigit()
        ]
        if numeric_branch_ids:
            return queryset.filter(branchAccess__id__in=numeric_branch_ids).distinct()
        return queryset.none() if hasattr(queryset, "none") else []
    except Exception:
        # Fallback to empty list if there's any error
        return []
