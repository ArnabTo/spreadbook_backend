from django.apps import AppConfig


class InventoryLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory_log"

    def ready(self):
        from django.db.models.signals import post_save
        from inventory_log import signals as inv_signals

        try:
            from purchase.models import PurchaseOrder

            post_save.connect(inv_signals.log_purchase_order_paid, sender=PurchaseOrder)
        except Exception:
            pass

        try:
            from sales.models import Sale

            post_save.connect(inv_signals.log_sale_created, sender=Sale)
        except Exception:
            pass

        try:
            from expense.models import Expense

            post_save.connect(inv_signals.log_expense_created, sender=Expense)
        except Exception:
            pass
