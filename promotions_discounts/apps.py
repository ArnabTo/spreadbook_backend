from django.apps import AppConfig


class PromotionsDiscountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "promotions_discounts"
    verbose_name = "Promotions & Discounts"

    def ready(self):
        import promotions_discounts.signals
