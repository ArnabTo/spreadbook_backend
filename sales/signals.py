from django.db import transaction
from django.db.models import Sum
from django.db.models import F
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from sales.models import Sale


@receiver(pre_save, sender="sales.InvoiceItem")
def _invoice_item_pre_save(sender, instance, **kwargs):
    """Capture previous quantity/product so we can apply deltas in post_save."""
    if not instance.pk:
        instance._previous_quantity = 0
        instance._previous_product_id = None
        return

    try:
        prev = sender.objects.only("quantity", "product_id").get(pk=instance.pk)
        instance._previous_quantity = int(prev.quantity or 0)
        instance._previous_product_id = prev.product_id
    except sender.DoesNotExist:
        instance._previous_quantity = 0
        instance._previous_product_id = None


@receiver(post_save, sender="sales.InvoiceItem")
def _invoice_item_post_save(sender, instance, created, **kwargs):
    """Keep products.Product.totalSold updated from POS billing items."""
    from django.db.models.functions import Greatest
    from products.models.product_model import Product

    new_qty = int(getattr(instance, "quantity", 0) or 0)
    new_product_id = getattr(instance, "product_id", None)

    prev_qty = int(getattr(instance, "_previous_quantity", 0) or 0)
    prev_product_id = getattr(instance, "_previous_product_id", None)

    if created:
        prev_qty = 0
        prev_product_id = None

    # Nothing to update if no product.
    if not new_product_id and not prev_product_id:
        return

    # If product changed, subtract from old and add to new.
    if prev_product_id and prev_product_id != new_product_id:
        Product.objects.filter(id=prev_product_id).update(
            totalSold=Greatest(F("totalSold") - prev_qty, 0)
        )
        if new_product_id:
            Product.objects.filter(id=new_product_id).update(
                totalSold=F("totalSold") + new_qty
            )
        return

    # Same product: apply quantity delta.
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


@receiver(post_delete, sender="sales.InvoiceItem")
def _invoice_item_post_delete(sender, instance, **kwargs):
    """Rollback totalSold when an invoice item is deleted."""
    from django.db.models.functions import Greatest
    from products.models.product_model import Product

    product_id = getattr(instance, "product_id", None)
    if not product_id:
        return

    qty = int(getattr(instance, "quantity", 0) or 0)
    if qty <= 0:
        return

    Product.objects.filter(id=product_id).update(
        totalSold=Greatest(F("totalSold") - qty, 0)
    )


# @receiver(post_save, sender=Sale)
# def discount(sender, instance, created, **kwargs):
#     ''' Sales discount calculation '''
#     with transaction.atomic():
#         if instance.discount != 0:
#             # Discount calculate Formula: original_price - (original_price * discount / 100)
#             discounted_price = instance.total - (instance.total * instance.discount / 100)
#             Sale.objects.filter(id=instance.id).update(total=discounted_price)


# @receiver(post_save, sender=Sale)
# def due(sender, instance, created, **kwargs):
#     ''' Sales due calculation '''
#     with transaction.atomic():
#         due_amount = Sale.objects.filter(id=instance.id).aggregate(Sum('due'))['due__sum']
#         total_amount = Sale.objects.filter(id=instance.id).aggregate(Sum('total'))['total__sum']
#         payable_amount = due_amount + total_amount
#         Sale.objects.filter(id=instance.id).update(total=payable_amount)
