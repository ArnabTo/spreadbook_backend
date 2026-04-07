import random
import string
import uuid
from collections import defaultdict

from django.db import models
from django.utils.timezone import now


class StockTransfer(models.Model):
    TRANSFER_TYPE_CHOICES = (
        ("warehouse_to_branch", "Warehouse → Branch"),
        ("branch_to_warehouse", "Branch → Warehouse"),
        ("warehouse_to_warehouse", "Warehouse → Warehouse"),
        ("branch_to_branch", "Branch → Branch"),
    )
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("in_transit", "In Transit"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer_number = models.CharField(max_length=32, unique=True, db_index=True)
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="stock_transfers",
    )
    transfer_type = models.CharField(max_length=30, choices=TRANSFER_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", db_index=True
    )

    source_warehouse = models.ForeignKey(
        "company.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_transfers",
    )
    source_branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_transfers",
    )

    # Destination location
    destination_warehouse = models.ForeignKey(
        "company.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transfers",
    )
    destination_branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transfers",
    )

    notes = models.TextField(blank=True, null=True)
    transferred_by = models.CharField(max_length=100, blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["company", "status"], name="idx_transfer_company_status"
            ),
            models.Index(
                fields=["company", "transfer_type"], name="idx_transfer_company_type"
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.transfer_number:
            suffix = "".join(random.choices(string.digits, k=8))
            self.transfer_number = f"TRF-{suffix}"
        super().save(*args, **kwargs)

    def complete_transfer(self):
        """
        Execute the transfer:
          1. Update each non-rejected ProductSerialItem's location fields and status.
          2. Adjust StockSummary (subtract from source, add to destination).
          3. Mark transfer as completed.

        The StockSummary post_save signal then auto-recalculates Product.in_stock.
        """
        if self.status not in ("draft", "in_transit"):
            raise ValueError(f"Cannot complete a transfer with status '{self.status}'")

        transfer_items = self.items.select_related("serial_item", "product", "variant")
        dest_is_branch = self.destination_branch_id is not None

        # Count non-rejected items per (product, variant) to bulk-adjust summaries
        product_variant_count: dict[tuple, int] = defaultdict(int)

        for ti in transfer_items:
            if ti.status == "rejected":
                continue

            serial = ti.serial_item
            if dest_is_branch:
                serial.status = "in_branch"
                serial.branch_id = self.destination_branch_id
                serial.warehouse_id = None
            else:
                serial.status = "in_warehouse"
                serial.warehouse_id = self.destination_warehouse_id
                serial.branch_id = None
            serial.save(update_fields=["status", "branch_id", "warehouse_id"])

            ti.status = "transferred"
            ti.save(update_fields=["status"])

            product_variant_count[(ti.product_id, ti.variant_id)] += 1

        for (product_id, variant_id), count in product_variant_count.items():
            self._adjust_summary(
                product_id=product_id,
                variant_id=variant_id,
                warehouse_id=self.source_warehouse_id,
                branch_id=self.source_branch_id,
                location="in_warehouse" if self.source_warehouse_id else "in_branch",
                delta=-count,
            )
            self._adjust_summary(
                product_id=product_id,
                variant_id=variant_id,
                warehouse_id=self.destination_warehouse_id,
                branch_id=self.destination_branch_id,
                location=(
                    "in_warehouse" if self.destination_warehouse_id else "in_branch"
                ),
                delta=count,
            )

        self.status = "completed"
        self.completed_at = now()
        self.save(update_fields=["status", "completed_at"])

    def _adjust_summary(
        self, product_id, variant_id, warehouse_id, branch_id, location, delta
    ):
        from .inventory_model import ProductBranchInventory

        summary, _ = ProductBranchInventory.objects.get_or_create(
            companyId_id=self.company_id,
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
            branch_id=branch_id,
            defaults={"location": location, "quantity": 0},
        )
        summary.quantity = max(0, summary.quantity + delta)
        summary.location = location
        summary.save(update_fields=["quantity", "location"])

    def __str__(self):
        return self.transfer_number


class StockTransferItem(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("transferred", "Transferred"),
        ("rejected", "Rejected"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name="items",
    )
    serial_item = models.ForeignKey(
        "products.ProductSerialItem",
        on_delete=models.PROTECT,
        related_name="transfer_items",
    )
    # Denormalized for fast reporting without extra joins
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="transfer_items",
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfer_items",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["transfer", "serial_item"],
                name="uniq_transfer_serial_item",
            )
        ]
        indexes = [
            models.Index(
                fields=["transfer", "status"],
                name="idx_transfer_item_status",
            ),
        ]

    def __str__(self):
        return f"{self.transfer} / {self.serial_item}"
