"""
Auto-create a SupplierLedger entry whenever a PurchaseOrder with a supplier
is created. Also update the ledger's debit_amount if the PO total changes.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="purchase.PurchaseOrder")
def sync_ledger_on_po_save(sender, instance, created, **kwargs):
    """Create or update the SupplierLedger linked to this PurchaseOrder."""
    po = instance

    # Only create/update ledger when the PO has a supplier
    if po.supplier_id is None:
        return

    # Determine company: prefer branch's company, then fall back to nothing
    company = None
    if po.branch_id:
        try:
            from company.models import Branch
            branch = Branch.objects.select_related(
                "company").filter(id=po.branch_id).first()
            if branch:
                company = branch.company
        except Exception:
            pass

    if company is None:
        # Try to resolve from supplier's company
        try:
            from suppliers.models import Supplier
            supplier = Supplier.objects.select_related(
                "companyId").filter(id=po.supplier_id).first()
            if supplier and supplier.companyId:
                company = supplier.companyId
        except Exception:
            pass

    if company is None:
        return  # Cannot create ledger without a company

    from supplier_ledger.models import SupplierLedger

    ledger, _ = SupplierLedger.objects.get_or_create(
        purchase_order=po,
        defaults=dict(
            company=company,
            branch=po.branch,
            supplier_id=po.supplier_id,
            debit_amount=po.total_amount or 0,
            balance=po.total_amount or 0,
            po_number=po.po_number or "",
            po_date=po.order_date,
        ),
    )

    # On subsequent saves (e.g. total_amount recalc), keep debit in sync
    if not _:
        updated = False
        if ledger.debit_amount != (po.total_amount or 0):
            ledger.debit_amount = po.total_amount or 0
            updated = True
        if ledger.po_number != (po.po_number or ""):
            ledger.po_number = po.po_number or ""
            updated = True
        if po.branch_id and ledger.branch_id != po.branch_id:
            ledger.branch_id = po.branch_id
            updated = True
        if updated:
            ledger.save(update_fields=["debit_amount",
                        "po_number", "branch", "updated_at"])
            ledger.recalc()
