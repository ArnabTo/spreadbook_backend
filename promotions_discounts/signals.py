from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Promotion, PromotionUsage


@receiver(pre_save, sender=Promotion)
def update_promotion_status(sender, instance, **kwargs):
    """Auto-update promotion status based on dates"""
    now = timezone.now()

    # Only update status if it's not manually set to inactive
    if instance.status != "inactive":
        if instance.start_date > now:
            instance.status = "scheduled"
        elif instance.end_date < now:
            instance.status = "expired"
        elif instance.start_date <= now <= instance.end_date:
            instance.status = "active"


@receiver(post_save, sender=PromotionUsage)
def update_promotion_usage_count(sender, instance, created, **kwargs):
    """Update promotion usage count when a new usage is created"""
    if created:
        promotion = instance.promotion
        promotion.used_count += 1

        # Check if usage limit is reached
        if promotion.used_count >= promotion.usage_limit:
            promotion.status = "inactive"

        promotion.save(update_fields=["used_count", "status"])


# Signal to auto-expire promotions (could be called by a cron job)
def expire_promotions():
    """Expire promotions that have passed their end date"""
    now = timezone.now()
    expired_count = Promotion.objects.filter(
        end_date__lt=now, status__in=["active", "scheduled"]
    ).update(status="expired")

    return expired_count


# Signal to activate scheduled promotions (could be called by a cron job)
def activate_scheduled_promotions():
    """Activate promotions that should now be active"""
    now = timezone.now()
    activated_count = Promotion.objects.filter(
        start_date__lte=now, end_date__gte=now, status="scheduled"
    ).update(status="active")

    return activated_count
