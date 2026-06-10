from django.db import models


class ProductUnitPrice(models.Model):
    """Per-unit pricing for products with multiple measuring units enabled."""

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="unit_prices",
    )
    measuring_unit = models.ForeignKey(
        "products.Unit",
        on_delete=models.CASCADE,
        related_name="unit_prices",
        help_text="Measuring unit for this price row",
    )
    sales_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = [("product", "measuring_unit")]
        ordering = ["id"]

    def __str__(self):
        return f"{self.product} — {self.measuring_unit} (S:{self.sales_price} / P:{self.purchase_price})"
