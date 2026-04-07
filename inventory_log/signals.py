"""
InventoryLog signal handlers.
Connected in InventoryLogConfig.ready() — not via @receiver decorators
so we can pass the actual model class as sender (string senders don't work
with Django's post_save).
"""

from inventory_log.models import InventoryLog


def _log_if_missing(reference, category, defaults):
    """Create a log entry only if one with the same reference+category doesn't exist."""
    if not InventoryLog.objects.filter(reference=reference, category=category).exists():
        InventoryLog.objects.create(reference=reference, category=category, **defaults)


def _upsert_log(reference, category, defaults):
    """
    Create or update a log entry for reference+category.
    Used for sales where the first post_save fires before totalAmount is populated;
    subsequent saves with real values will overwrite the initial zeros.
    """
    InventoryLog.objects.update_or_create(
        reference=reference,
        category=category,
        defaults=defaults,
    )


def log_purchase_order_paid(sender, instance, **kwargs):
    """Create an inventory IN log when a PO is marked as paid."""
    if instance.payment_status == "paid":
        _log_if_missing(
            reference=instance.po_number or str(instance.id),
            category="purchase",
            defaults={
                "log_type": "in",
                "amount": instance.total_amount or 0,
                "quantity": 0,
                "description": f"Purchase Order {instance.po_number} paid",
                "companyId": instance.companyId,
                "branch": instance.branch,
            },
        )


def log_sale_created(sender, instance, **kwargs):
    """
    Create or update an inventory OUT log when a sale is paid.
    We use update_or_create (not _log_if_missing) because Sale.save() generates
    the order_number synchronously, so the very first post_save fires with
    is_paid=True but totalAmount still 0. The serializer then sets totalAmount
    and calls save() again — we must overwrite that initial zero entry.
    We skip entirely when totalAmount == 0 to avoid noisy zero-value logs.
    """
    if not instance.is_paid:
        return
    amount = instance.totalAmount or 0
    if amount == 0:
        return
    ref = instance.order_number or str(instance.id)
    _upsert_log(
        reference=ref,
        category="sale",
        defaults={
            "log_type": "out",
            "amount": amount,
            "quantity": instance.totalQty or 0,
            "description": f"Sale {ref}",
            "companyId": instance.companyId,
            "branch": instance.branch,
        },
    )


def log_expense_created(sender, instance, created, **kwargs):
    """Create an OUT log when a new expense is recorded."""
    if created:
        ref = instance.expense_number or str(instance.id)
        _log_if_missing(
            reference=ref,
            category="expense",
            defaults={
                "log_type": "out",
                "amount": float(instance.amount) if instance.amount else 0,
                "quantity": 0,
                "description": instance.description or f"Expense {ref}",
                "companyId": None,
                "branch": None,
            },
        )
