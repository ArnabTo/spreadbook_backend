from django.apps import AppConfig


class SupplierLedgerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "supplier_ledger"
    verbose_name = "Supplier Ledger"

    def ready(self):
        import supplier_ledger.signals  # noqa: F401
