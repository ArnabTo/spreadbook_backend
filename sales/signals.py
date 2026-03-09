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
        instance._previous_sold_in_secondary_unit = bool(prev.sold_in_secondary_unit)
    except sender.DoesNotExist:
        instance._previous_quantity = 0
        instance._previous_product_id = None
        instance._previous_sold_in_secondary_unit = False


# ──────────────────────────────────────────────────────────────────────────────
# Shared stock-adjustment helper
# ──────────────────────────────────────────────────────────────────────────────


def _apply_stock_delta(
    product_id,
    quantity: int,
    sold_in_secondary: bool,
    *,
    reverse: bool = False,
) -> None:
    """Adjust Product stock by ±quantity.

    Rules
    -----
    1. **No secondary unit configured** (or ``sold_in_secondary=False``):
       Adjust ``in_stock`` (primary / Box).
       ``Product.save()`` auto-recomputes ``in_stock_secondary``.

    2. **Has secondary unit + sold_in_secondary=True** (e.g. Strips):
       Adjust ``in_stock_secondary`` directly.
       Recompute ``in_stock = ceil(in_stock_secondary / factor)``.
       Uses a direct ``.update()`` to prevent ``Product.save()`` from
       overwriting the secondary count with ``in_stock × factor``.

    ``reverse=True`` adds stock back (used for refunds / deletions).
    """
    from django.utils.timezone import now as tz_now

    from products.models.product_model import Product

    if not product_id or quantity <= 0:
        return

    sign = 1 if reverse else -1  # +1 to restore, -1 to deduct

    try:
        with transaction.atomic():
            product = (
                Product.objects.select_for_update()
                .only(
                    "in_stock",
                    "in_stock_secondary",
                    "unit_conversion_factor",
                    "secondary_unit_id",
                    "low_stock_threshold",
                )
                .get(pk=product_id)
            )

            factor = int(getattr(product, "unit_conversion_factor", 0) or 0)
            has_secondary = (
                getattr(product, "secondary_unit_id", None) is not None and factor > 0
            )

            if sold_in_secondary and has_secondary:
                # Secondary-unit path (e.g. sell/return Strips)
                cur_sec = int(getattr(product, "in_stock_secondary", 0) or 0)
                new_sec = max(cur_sec + sign * quantity, 0)

                # means boxes never decrease when selling fewer than factor strips at once.
                new_boxes = new_sec // factor

                low = int(getattr(product, "low_stock_threshold", 20) or 20)
                if new_boxes == 0:
                    new_status, new_inv = "out of stock", "out of stock"
                elif new_boxes <= low:
                    new_status, new_inv = "in stock", "low stock"
                else:
                    new_status, new_inv = "in stock", "in stock"

                # in_stock_secondary = in_stock × factor and losing our value.
                Product.objects.filter(pk=product.pk).update(
                    in_stock=new_boxes,
                    in_stock_secondary=new_sec,
                    available=new_boxes,
                    status=new_status,
                    inventoryType=new_inv,
                    out_of_stock=(new_boxes == 0),
                    updateAt=tz_now(),
                )

            else:
                # Primary-unit path (e.g. sell/return whole Boxes)
                # Use direct .update() instead of product.save() to avoid Product.save()
                cur_stock = int(getattr(product, "in_stock", 0) or 0)
                new_stock = max(cur_stock + sign * quantity, 0)

                # Derive secondary stock from the new primary count (same formula as Product.save).
                new_sec = new_stock * factor if has_secondary else 0

                low = int(getattr(product, "low_stock_threshold", 20) or 20)
                if new_stock == 0:
                    new_status, new_inv = "out of stock", "out of stock"
                elif new_stock <= low:
                    new_status, new_inv = "in stock", "low stock"
                else:
                    new_status, new_inv = "in stock", "in stock"

                Product.objects.filter(pk=product.pk).update(
                    in_stock=new_stock,
                    in_stock_secondary=new_sec,
                    available=new_stock,
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
        return  # POS items are immutable after creation; no quantity-edit path.

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
                ProductVariant.objects.filter(pk=variant_id).update(size_qty=new_qty)
            except ProductVariant.DoesNotExist:
                pass

    # ── Product-level stock ────────────────────────────────────────────────
    # Skip branch + primary-unit + non-variant: adjust_branch_stock() already
    # handled it in the serializer.
    # For variant products we always run _apply_stock_delta so Product.in_stock
    # stays in sync with total variant quantities sold.
    if branch_id is not None and not sold_in_sec and variant_id is None:
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

    # Mirror the create logic: skip branch + primary-unit + non-variant items.
    if branch_id is not None and not sold_in_sec and variant_id is None:
        return  # Branch-inventory rollback is not managed here.
    _apply_stock_delta(product_id, qty, sold_in_sec, reverse=True)
