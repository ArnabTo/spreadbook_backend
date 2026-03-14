from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from products.models.product_model import Product, ProductVariant, ProductSerialItem
from django.db import transaction

from purchase.models import PurchaseOrder, PurchaseOrderItem


@receiver(post_save, sender=Product)
def sync_inventory_item_from_product(sender, instance: Product, **kwargs):
    """Keep linked InventoryItem stock aligned with Product.in_stock (used by POS)."""
    try:
        inventory_item = instance.inventory_item
    except Exception:
        return

    desired_stock = Decimal(instance.in_stock or 0)
    needs_save = False

    if inventory_item.current_stock != desired_stock:
        inventory_item.current_stock = desired_stock
        needs_save = True

    if (
        instance.exp_date
        and getattr(inventory_item, "expiry_date", None) != instance.exp_date
    ):
        inventory_item.expiry_date = instance.exp_date
        needs_save = True

    if needs_save:
        inventory_item.save(sync_product=False)


@receiver(pre_save, sender=Product)
def track_product_stock(sender, instance, **kwargs):
    """
    Tracks the product stock and updates the product stock status.
    """
    if instance.in_stock <= 0:
        print(f"{instance.name} is out of stock")
    else:
        print(f"{instance.name} is in stock")


@receiver(pre_save, sender=Product)
def capture_purchase_relevant_product_fields(sender, instance: Product, **kwargs):
    """Capture previous supplier/cost state to decide PO creation on update."""
    if not instance.pk:
        instance._prev_supplier_id_for_po = None
        instance._prev_supplier_price_for_po = None
        return

    previous = (
        Product.objects.filter(pk=instance.pk)
        .values("supplier_id", "supplier_price")
        .first()
    )
    instance._prev_supplier_id_for_po = (
        previous.get("supplier_id") if previous else None
    )
    instance._prev_supplier_price_for_po = (
        previous.get("supplier_price") if previous else None
    )


def _safe_decimal(value, fallback="0") -> Decimal:
    try:
        return Decimal(str(value if value is not None else fallback))
    except Exception:
        return Decimal(str(fallback))


@receiver(post_save, sender=Product)
def create_purchase_order_from_product(sender, instance: Product, created, **kwargs):
    """Create or update Purchase Order when a product is created/updated.

    - On product creation without supplier: creates PO without supplier
    - On product update adding supplier: updates existing PO with supplier
    - PO total_amount is sum of (quantity * supplier_price) for all items
    - Variant details are included as PO item lines when variants exist
    - Uses variant.supplier_price if set, otherwise Product.supplier_price
    """

    current_supplier_id = getattr(instance, "supplier_id", None)
    current_supplier_price = _safe_decimal(
        getattr(instance, "supplier_price", 0))
    prev_supplier_id = getattr(instance, "_prev_supplier_id_for_po", None)
    prev_supplier_price = _safe_decimal(
        getattr(instance, "_prev_supplier_price_for_po", None)
    )

    # Determine if we should create/update PO
    supplier_changed = current_supplier_id != prev_supplier_id
    price_changed = current_supplier_price != prev_supplier_price
    should_process_po = created or supplier_changed or price_changed

    if not should_process_po:
        return

    def _process_po():
        with transaction.atomic():
            # Check if product already has a PO (for update case)
            existing_po = (
                PurchaseOrder.objects.filter(
                    notes__contains=f"Product {instance.id}")
                .order_by("-created_at")
                .first()
            )

            if existing_po and not created and supplier_changed:
                # Update existing PO with new supplier
                existing_po.supplier_id = current_supplier_id
                existing_po.branch_id = getattr(instance, "branch_id", None)
                existing_po.warehouse_id = getattr(
                    instance, "warehouse_id", None)
                existing_po.companyId_id = getattr(
                    instance, "companyId_id", None)
                po = existing_po
                # Delete old items to recreate
                existing_po.items.all().delete()
            elif existing_po and not created and price_changed:
                # Update existing PO with new price
                existing_po.branch_id = getattr(instance, "branch_id", None)
                existing_po.warehouse_id = getattr(
                    instance, "warehouse_id", None)
                existing_po.companyId_id = getattr(
                    instance, "companyId_id", None)
                po = existing_po
                # Delete old items to recreate
                existing_po.items.all().delete()
            else:
                # Create new PO
                po = PurchaseOrder.objects.create(
                    supplier_id=current_supplier_id,
                    branch_id=getattr(instance, "branch_id", None),
                    warehouse_id=getattr(instance, "warehouse_id", None),
                    companyId_id=getattr(instance, "companyId_id", None),
                    status="pending",
                    notes=f"Auto-created from Product {instance.name or instance.id}",
                    created_by="system:product-signal",
                )

            variants = list(instance.variants.all())

            total_amount = Decimal("0")

            if variants:
                for variant in variants:
                    variant_desc_parts = []
                    if getattr(variant, "size", None):
                        variant_desc_parts.append(f"size={variant.size}")
                    if getattr(variant, "color", None):
                        variant_desc_parts.append(f"color={variant.color}")
                    if getattr(variant, "size_name", None):
                        variant_desc_parts.append(
                            f"size_name={variant.size_name}")
                    if getattr(variant, "size_code", None):
                        variant_desc_parts.append(f"code={variant.size_code}")

                    variant_suffix = (
                        f" ({', '.join(variant_desc_parts)})"
                        if variant_desc_parts
                        else ""
                    )

                    # Use variant.supplier_price if available, otherwise Product.supplier_price
                    variant_supplier_price = _safe_decimal(
                        getattr(variant, "supplier_price", None)
                        or current_supplier_price
                    )
                    quantity = _safe_decimal(getattr(variant, "size_qty", 0))

                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        product=instance,
                        variant=variant,
                        variant_size=getattr(variant, "size", None) or None,
                        variant_color=getattr(variant, "color", None) or None,
                        variant_unique_code=getattr(
                            variant, "unique_code", None) or None,
                        name=f"{instance.name or 'Product'}{variant_suffix}",
                        quantity=quantity,
                        unit=str(getattr(instance, "unit", None) or "unit"),
                        unit_price=variant_supplier_price,
                    )

                    # Add to total amount
                    total_amount += quantity * variant_supplier_price
            else:
                # Use in_stock (Initial Stock) as quantity for products without variants
                quantity = _safe_decimal(getattr(instance, "in_stock", 0))
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=instance,
                    name=instance.name or "Product",
                    quantity=quantity,
                    unit=str(getattr(instance, "unit", None) or "unit"),
                    unit_price=current_supplier_price,
                )
                # Add to total amount
                total_amount += quantity * current_supplier_price

            # Set the calculated total amount
            po.total_amount = total_amount
            po.save(
                update_fields=["total_amount", "updated_at",
                               "supplier_id", "branch_id", "warehouse_id", "companyId_id"]
            )

    transaction.on_commit(_process_po)


@receiver(post_save, sender=ProductVariant)
def auto_generate_serial_items(sender, instance: ProductVariant, created, **kwargs):
    """
    Auto-create ProductSerialItem rows when a variant is saved.

    - On create: create size_qty serial items.
    - On update: if size_qty increased, create only the additional items.
      If decreased, existing physical units are not deleted (they exist in the real world).
    """
    qty = int(instance.size_qty or 0)
    if qty <= 0:
        return

    existing_count = ProductSerialItem.objects.filter(variant=instance).count()

    to_create = qty - existing_count
    if to_create <= 0:
        return  # qty unchanged or reduced — nothing to create

    warehouse_id = getattr(instance.product, "warehouse_id", None)

    def _create_serials():
        import random as _random
        import string as _string
        # Mirror ProductSerialItem.save() prefix logic for pre-generating codes
        if instance.unique_code:
            base = instance.unique_code
        elif instance.product and instance.product.unique_code:
            base = instance.product.unique_code
        else:
            base = "SER"
        # Load existing codes with this prefix to avoid collisions
        used_codes = set(
            ProductSerialItem.objects.filter(
                serial_code__startswith=base + "-"
            ).values_list("serial_code", flat=True)
        )
        # Find the most recent PO created for this product (auto-created by signal)
        po_id = (
            PurchaseOrder.objects.filter(
                notes__contains=f"Product {instance.product.id}"
            )
            .order_by("-created_at")
            .values_list("uuid", flat=True)
            .first()
        )
        items = []
        for _ in range(to_create):
            while True:
                suffix = ''.join(_random.choices(
                    _string.digits + _string.ascii_uppercase, k=6))
                code = f"{base}-{suffix}"
                if code not in used_codes:
                    used_codes.add(code)
                    break
            items.append(ProductSerialItem(
                product=instance.product,
                variant=instance,
                warehouse_id=warehouse_id,
                status="in_warehouse",
                serial_code=code,
                purchase_order_id=po_id,
            ))
        ProductSerialItem.objects.bulk_create(items, batch_size=500)

    transaction.on_commit(_create_serials)
