from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from products.models.product_model import Product


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
