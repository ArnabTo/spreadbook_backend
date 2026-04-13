from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from sales.models import Sale  # noqa: F401


# ──────────────────────────────────────────────────────────────────────────────
# InvoiceItem – capture previous state before any update
# ──────────────────────────────────────────────────────────────────────────────


@receiver(pre_save, sender="sales.InvoiceItem")
def _invoice_item_pre_save(sender, instance, **kwargs):
    """Capture previous quantity / product / unit-mode so post_save can apply deltas."""
    if not instance.pk:
        instance._previous_quantity = 0
        instance._previous_product_id = None
        instance._previous_sold_in_secondary_unit = False
        return

    try:
        prev = sender.objects.only(
            "quantity", "product_id", "sold_in_secondary_unit"
        ).get(pk=instance.pk)
        instance._previous_quantity = int(prev.quantity or 0)
        instance._previous_product_id = prev.product_id
        instance._previous_sold_in_secondary_unit = bool(
            prev.sold_in_secondary_unit)
    except sender.DoesNotExist:
        instance._previous_quantity = 0
        instance._previous_product_id = None
        instance._previous_sold_in_secondary_unit = False


# ──────────────────────────────────────────────────────────────────────────────
# Shared stock-adjustment helper
# ──────────────────────────────────────────────────────────────────────────────


def _apply_stock_delta(
    product_id,
    quantity,
    sold_in_sec: bool = False,
    *,
    reverse: bool = False,
) -> None:
    """Adjust Product stock by ±quantity in base units.

    ``reverse=True`` adds stock back (used for refunds / deletions).
    """
    from django.utils.timezone import now as tz_now

    from products.models.product_model import Product

    if not product_id:
        return

    try:
        quantity_dec = Decimal(str(quantity))
    except Exception:
        return

    if quantity_dec <= 0:
        return

    sign = 1 if reverse else -1  # +1 to restore, -1 to deduct

    try:
        with transaction.atomic():
            product = (
                Product.objects.select_for_update()
                .only("in_stock", "low_stock_threshold")
                .get(pk=product_id)
            )

            cur_stock = Decimal(str(getattr(product, "in_stock", 0) or 0))
            new_stock = max(cur_stock + sign * quantity_dec, Decimal("0"))

            low = int(getattr(product, "low_stock_threshold", 20) or 20)
            if new_stock == 0:
                new_status, new_inv = "out of stock", "out of stock"
            elif new_stock <= low:
                new_status, new_inv = "in stock", "low stock"
            else:
                new_status, new_inv = "in stock", "in stock"

            Product.objects.filter(pk=product.pk).update(
                in_stock=new_stock,
                available=int(new_stock),
                status=new_status,
                inventoryType=new_inv,
                out_of_stock=(new_stock == 0),
                updateAt=tz_now(),
            )

    except Product.DoesNotExist:
        return


# ──────────────────────────────────────────────────────────────────────────────
# InvoiceItem – stock deduction on creation
# ──────────────────────────────────────────────────────────────────────────────


@receiver(post_save, sender="sales.InvoiceItem")
def _invoice_item_stock_deduct(sender, instance, created, **kwargs):
    """Deduct product stock (and variant size_qty) when a new InvoiceItem is created.

    Stock pool selection
    --------------------
    * ``sold_in_secondary_unit=True``  + product has secondary unit
      → deduct from ``in_stock_secondary``  (e.g. Strips), recompute boxes.
    * ``sold_in_secondary_unit=False`` or no secondary unit on product
      → deduct from ``in_stock``  (primary / Box).
    * Variant product (``variant_id`` set)
      → additionally deduct from ``ProductVariant.size_qty``.
    """
    if not created:
        # POS items are immutable after creation; no quantity-edit path.
        return

    product_id = getattr(instance, "product_id", None)
    if not product_id:
        return

    quantity = int(getattr(instance, "quantity", 0) or 0)
    sold_in_sec = bool(getattr(instance, "sold_in_secondary_unit", False))
    variant_id = getattr(instance, "variant_id", None)

    try:
        branch_id = getattr(instance.sell_invoice, "branch_id", None)
    except Exception:
        branch_id = None

    # ── Variant stock: reduce ProductVariant.size_qty ──────────────────────
    # This is the single place that decrements variant qty (serializer no longer does it).
    if variant_id is not None and quantity > 0:
        from products.models import ProductVariant

        with transaction.atomic():
            try:
                v = (
                    ProductVariant.objects.select_for_update()
                    .only("size_qty")
                    .get(pk=variant_id)
                )
                new_qty = max(0, (v.size_qty or 0) - quantity)
                ProductVariant.objects.filter(
                    pk=variant_id).update(size_qty=new_qty)
            except ProductVariant.DoesNotExist:
                pass

    # ── Product-level stock ────────────────────────────────────────────────
    # Skip branch + non-variant items: adjust_branch_stock() already handled
    # the deduction in serializer for both primary and secondary unit sales.
    # For variant products we still run _apply_stock_delta so Product.in_stock
    # stays in sync when variant rows are sold.
    if branch_id is not None and variant_id is None:
        return

    _apply_stock_delta(product_id, quantity, sold_in_sec, reverse=False)


# ──────────────────────────────────────────────────────────────────────────────
# InvoiceItem – totalSold tracking
# ──────────────────────────────────────────────────────────────────────────────


@receiver(post_save, sender="sales.InvoiceItem")
def _invoice_item_post_save(sender, instance, created, **kwargs):
    """Keep products.Product.totalSold in sync with POS billing items."""
    from django.db.models.functions import Greatest

    from products.models.product_model import Product

    new_qty = int(getattr(instance, "quantity", 0) or 0)
    new_product_id = getattr(instance, "product_id", None)

    prev_qty = int(getattr(instance, "_previous_quantity", 0) or 0)
    prev_product_id = getattr(instance, "_previous_product_id", None)

    if created:
        prev_qty = 0
        prev_product_id = None

    if not new_product_id and not prev_product_id:
        return

    # Product changed → subtract from old, add to new.
    if prev_product_id and prev_product_id != new_product_id:
        Product.objects.filter(id=prev_product_id).update(
            totalSold=Greatest(F("totalSold") - prev_qty, 0)
        )
        if new_product_id:
            Product.objects.filter(id=new_product_id).update(
                totalSold=F("totalSold") + new_qty
            )
        return

    # Same product – apply quantity delta.
    if new_product_id:
        delta = new_qty - prev_qty
        if delta > 0:
            Product.objects.filter(id=new_product_id).update(
                totalSold=F("totalSold") + delta
            )
        elif delta < 0:
            Product.objects.filter(id=new_product_id).update(
                totalSold=Greatest(F("totalSold") + delta, 0)
            )


# ──────────────────────────────────────────────────────────────────────────────
# InvoiceItem – stock + totalSold rollback on deletion
# ──────────────────────────────────────────────────────────────────────────────


@receiver(post_delete, sender="sales.InvoiceItem")
def _invoice_item_post_delete(sender, instance, **kwargs):
    """Restore product stock and totalSold when an invoice item is deleted."""
    from django.db.models.functions import Greatest

    from products.models.product_model import Product

    product_id = getattr(instance, "product_id", None)
    if not product_id:
        return

    qty = int(getattr(instance, "quantity", 0) or 0)
    if qty <= 0:
        return

    # Restore totalSold.
    Product.objects.filter(id=product_id).update(
        totalSold=Greatest(F("totalSold") - qty, 0)
    )

    # Mirror the create logic: only skip restoration for branch + primary-unit items
    # (those were handled by adjust_branch_stock and have no signal-managed stock entry).
    sold_in_sec = bool(getattr(instance, "sold_in_secondary_unit", False))
    variant_id = getattr(instance, "variant_id", None)

    try:
        branch_id = getattr(instance.sell_invoice, "branch_id", None)
    except Exception:
        branch_id = None

    # ── Restore variant size_qty ─────────────────────────────────────────────
    if variant_id is not None and qty > 0:
        from products.models import ProductVariant

        with transaction.atomic():
            try:
                v = (
                    ProductVariant.objects.select_for_update()
                    .only("size_qty")
                    .get(pk=variant_id)
                )
                ProductVariant.objects.filter(pk=variant_id).update(
                    size_qty=(v.size_qty or 0) + qty
                )
            except ProductVariant.DoesNotExist:
                pass

    # Mirror the create logic: skip branch + non-variant items.
    if branch_id is not None and variant_id is None:
        return  # Branch-inventory rollback is not managed here.
    _apply_stock_delta(product_id, qty, sold_in_sec, reverse=True)
