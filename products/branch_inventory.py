from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db import transaction


@dataclass(frozen=True)
class EffectiveProductNumbers:
    price: Decimal
    priceSale: Decimal
    regular_price: Decimal
    in_stock: int
    available: int


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def resolve_branch_from_request(request, *, product=None):
    """Resolve a Branch for per-branch inventory.

    Priority:
    1) `branch_id`/`branchId` query param
    2) product.branch (legacy branch-scoped products)
    3) user's single branchAccess (if exactly one)
    """

    from company.models import Branch as CompanyBranch

    branch_id = None
    if request is not None:
        branch_id = request.query_params.get("branch_id") or request.query_params.get(
            "branchId"
        )

    if branch_id:
        return CompanyBranch.objects.filter(id=branch_id).first()

    if product is not None and getattr(product, "branch_id", None):
        return getattr(product, "branch", None)

    user = getattr(request, "user", None) if request is not None else None
    if (
        user is not None
        and getattr(user, "is_authenticated", False)
        and hasattr(user, "branchAccess")
    ):
        try:
            qs = user.branchAccess.all()
            if qs.count() == 1:
                return qs.first()
        except Exception:
            return None

    return None


def get_or_create_branch_inventory(product, branch):
    from products.models import ProductBranchInventory

    if product is None or branch is None:
        return None

    inv = (
        ProductBranchInventory.objects.select_for_update()
        .filter(product=product, branch=branch)
        .first()
    )
    if inv:
        return inv

    # Seed per-branch stock:
    # - If the product is already branch-scoped to this branch (legacy data), seed from Product.
    # - If the product is shared (branch=NULL) or for a different branch, start stock at 0.
    if getattr(product, "branch_id", None) and str(product.branch_id) == str(branch.id):
        stock_seed = int(getattr(product, "in_stock", 0) or 0)
    else:
        stock_seed = 0

    inv = ProductBranchInventory.objects.create(
        product=product,
        branch=branch,
        location="in_branch",
        companyId=getattr(product, "companyId", None)
        or getattr(branch, "company", None),
        price=getattr(product, "price", 0) or 0,
        priceSale=getattr(product, "priceSale", 0) or 0,
        regular_price=getattr(product, "regular_price", 0) or 0,
        quantity=stock_seed,
        low_stock_threshold=int(getattr(product, "low_stock_threshold", 20) or 20),
    )
    return inv


def get_effective_numbers(product, branch) -> EffectiveProductNumbers:
    """Read effective price + stock for the given branch.

    If no branch is provided, falls back to Product fields.
    """

    if branch is None:
        return EffectiveProductNumbers(
            price=_to_decimal(getattr(product, "price", 0)),
            priceSale=_to_decimal(getattr(product, "priceSale", 0)),
            regular_price=_to_decimal(getattr(product, "regular_price", 0)),
            in_stock=int(getattr(product, "in_stock", 0) or 0),
            available=int(getattr(product, "available", 0) or 0),
        )

    from products.models import ProductBranchInventory

    inv = (
        ProductBranchInventory.objects.filter(
            product=product, branch=branch, variant__isnull=True
        )
        .only("price", "priceSale", "regular_price", "quantity")
        .first()
    )
    if inv is None:
        # No branch-specific row yet.
        # Fall back to product-level stock so newly created products (which have no
        # branch inventory row seeded) are never incorrectly seen as zero-stock.
        return EffectiveProductNumbers(
            price=_to_decimal(getattr(product, "price", 0)),
            priceSale=_to_decimal(getattr(product, "priceSale", 0)),
            regular_price=_to_decimal(getattr(product, "regular_price", 0)),
            in_stock=int(getattr(product, "in_stock", 0) or 0),
            available=int(getattr(product, "available", 0) or 0),
        )

    return EffectiveProductNumbers(
        price=_to_decimal(inv.price) or _to_decimal(getattr(product, "price", 0)),
        priceSale=_to_decimal(inv.priceSale)
        or _to_decimal(getattr(product, "priceSale", 0)),
        regular_price=_to_decimal(inv.regular_price)
        or _to_decimal(getattr(product, "regular_price", 0)),
        in_stock=int(inv.quantity or 0),
        available=int(inv.quantity or 0),
    )


@transaction.atomic
def update_branch_fields(product, branch, *, fields: dict, updated_by=None):
    """Update branch-scoped product fields (price + stock) and keep legacy Product in sync when safe."""

    inv = get_or_create_branch_inventory(product, branch)
    if inv is None:
        return None

    # Normalize legacy field names: in_stock / available → quantity
    fields = dict(fields or {})
    if "in_stock" in fields and "quantity" not in fields:
        fields["quantity"] = fields.pop("in_stock")
    else:
        fields.pop("in_stock", None)
    if "available" in fields and "quantity" not in fields:
        fields["quantity"] = fields.pop("available")
    else:
        fields.pop("available", None)

    allowed = {"price", "priceSale", "regular_price", "quantity"}
    clean = {k: v for k, v in fields.items() if k in allowed}

    for k, v in clean.items():
        if k == "quantity":
            try:
                from decimal import Decimal as _D

                setattr(inv, k, _D(str(v or 0)))
            except Exception:
                setattr(inv, k, 0)
        else:
            try:
                setattr(inv, k, float(v or 0))
            except Exception:
                setattr(inv, k, 0)

    inv.save()
    # Signal (pbi_post_save) automatically recalculates Product.in_stock.

    return inv


@transaction.atomic
def adjust_branch_stock(
    product, branch, *, delta: int, reason: str = "", notes: str = "", updated_by=None
):
    inv = get_or_create_branch_inventory(product, branch)
    if inv is None:
        # Fallback for legacy flows (no branch)
        prev = int(getattr(product, "in_stock", 0) or 0)
        new = prev + int(delta)
        product.in_stock = new
        product.available = new
        try:
            product.save(
                update_fields=[
                    "in_stock",
                    "in_stock_secondary",
                    "available",
                    "updateAt",
                    "status",
                    "inventoryType",
                    "out_of_stock",
                ]
            )
        except Exception:
            product.save()
        return None

    from decimal import Decimal as _D

    prev = int(inv.quantity or 0)
    new = prev + int(delta)
    inv.quantity = _D(str(new))
    inv.save(update_fields=["quantity", "updated_at"])
    # Signal (pbi_post_save) automatically recalculates Product.in_stock.

    # Optional audit trail (best-effort)
    try:
        from products.models.inventory_model import ProductStockMovement

        ProductStockMovement.objects.create(
            product=product,
            movement_type="adjustment",
            quantity=Decimal(abs(int(delta))),
            previous_stock=Decimal(prev),
            new_stock=Decimal(new),
            reason=reason or "Branch stock adjusted",
            notes=(notes or "") + f" [branch={getattr(branch, 'id', '')}]",
            created_by=(
                getattr(updated_by, "username", None)
                if updated_by is not None
                and getattr(updated_by, "is_authenticated", False)
                else "System"
            ),
        )
    except Exception:
        pass

    return inv
