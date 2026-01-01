from __future__ import annotations

from django.db.models import Sum

from .models import Sale, RefundItem


def recalculate_sale_is_return(sale: Sale) -> bool:
    """Recalculate whether a sale is fully returned (fully refunded).

    Professional behavior:
    - A sale is considered returned only when all item quantities are fully refunded.
    - Partial refunds keep `Sale.is_return = False` so additional refunds can be applied.

    Returns the updated value.
    """

    order_items = list(sale.items.all())
    if not order_items:
        desired = False
    else:
        refunded_by_item_id = {
            int(row["invoice_item"]): int(row["qty"] or 0)
            for row in RefundItem.objects.filter(refund__sale=sale)
            .values("invoice_item")
            .annotate(qty=Sum("quantity"))
        }

        desired = True
        for item in order_items:
            original_qty = int(item.quantity or 0)
            if refunded_by_item_id.get(int(item.id), 0) < original_qty:
                desired = False
                break

    if sale.is_return != desired:
        sale.is_return = desired
        sale.save(update_fields=["is_return"])

    return desired
