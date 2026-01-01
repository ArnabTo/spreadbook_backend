from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
import uuid
from decimal import Decimal


class Promotion(models.Model):
    PROMOTION_TYPES = [
        ("percentage", "Percentage Off"),
        ("fixed", "Fixed Amount Off"),
        ("bogo", "Buy One Get One"),
        ("b2g1", "Buy 2 Get 1"),
        ("combo", "Combo / Bundle Price"),
        ("freeItem", "Free Item"),
    ]

    APPLICABLE_ON_CHOICES = [
        ("all", "All Items"),
        ("category", "Specific Category"),
        ("item", "Specific Item"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("scheduled", "Scheduled"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Name of the promotion")
    type = models.CharField(
        max_length=20,
        choices=PROMOTION_TYPES,
        default="percentage",
        help_text="Type of discount/promotion",
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Discount value (percentage or fixed amount)",
    )
    code = models.CharField(
        max_length=50, unique=True, help_text="Promotional code for customers"
    )
    start_date = models.DateTimeField(help_text="When the promotion starts")
    end_date = models.DateTimeField(help_text="When the promotion ends")
    min_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum order value to apply promotion",
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=999999,
        validators=[MinValueValidator(0)],
        help_text="Maximum discount amount",
    )
    usage_limit = models.PositiveIntegerField(
        default=999999, help_text="Maximum number of times this promotion can be used"
    )
    used_count = models.PositiveIntegerField(
        default=0, help_text="Number of times this promotion has been used"
    )
    applicable_on = models.CharField(
        max_length=20,
        choices=APPLICABLE_ON_CHOICES,
        default="all",
        help_text="What the promotion applies to",
    )
    target_items = models.JSONField(
        default=list,
        blank=True,
        help_text="List of target item IDs or category IDs (JSON array)",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        help_text="Current status of the promotion",
    )
    description = models.TextField(blank=True, help_text="Description of the promotion")

    # Metadata fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "authenticator.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_promotions",
    )
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="promotions",
        help_text="Company this promotion belongs to",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="promotions",
        help_text="Specific branch (optional, null means all branches)",
    )

    class Meta:
        db_table = "promotions_discounts_promotion"
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["company"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        # Auto-update status based on dates
        now = timezone.now()
        if self.start_date > now:
            self.status = "scheduled"
        elif self.end_date < now:
            self.status = "expired"
        elif self.status not in ["active", "inactive"]:
            self.status = "active"

        # Ensure code is uppercase
        self.code = self.code.upper()

        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if promotion is currently valid"""
        now = timezone.now()
        return (
            self.status == "active"
            and self.start_date <= now <= self.end_date
            and self.used_count < self.usage_limit
        )

    def can_apply_to_order(self, order_value):
        """Check if promotion can be applied to an order"""
        try:
            order_value_dec = Decimal(str(order_value or 0))
        except Exception:
            order_value_dec = Decimal("0")
        return self.is_valid() and order_value_dec >= Decimal(
            str(self.min_order_value or 0)
        )

    def calculate_discount(self, order_value):
        """Calculate discount amount for given order value"""
        if not self.can_apply_to_order(order_value):
            return 0

        order_value_dec = Decimal(str(order_value or 0))

        if self.type == "percentage":
            discount = order_value_dec * (Decimal(str(self.value)) / Decimal("100"))
        elif self.type == "fixed":
            discount = Decimal(str(self.value))
        else:
            # For BOGO and free item, discount calculation depends on specific items
            # This would need to be handled in the order processing logic
            return 0

        discount = min(discount, Decimal(str(self.max_discount)))
        discount = min(discount, order_value_dec)
        return float(discount)

    def calculate_discount_for_cart(self, order_value, items=None):
        """Calculate discount amount for a cart (order_value + item lines).

        Supported:
        - percentage, fixed (same as calculate_discount)
        - bogo: buy 1 get 1 free (per eligible item line)
        - b2g1: buy 2 get 1 free (per eligible item line)
        - combo: fixed bundle price for a required set of menu item IDs

        Cart item shape (dict): {id, category?, price, quantity}
        """
        if not self.can_apply_to_order(order_value):
            return Decimal("0")

        if self.type in {"percentage", "fixed"}:
            return Decimal(str(self.calculate_discount(order_value)))

        items = items or []

        def _d(v):
            return Decimal(str(v or 0))

        def _eligible(item):
            if self.applicable_on == "all":
                return True
            if self.applicable_on == "category":
                return str(item.get("category") or "") in set(
                    map(str, self.target_items or [])
                )
            if self.applicable_on == "item":
                return str(item.get("id") or "") in set(
                    map(str, self.target_items or [])
                )
            return False

        discount = Decimal("0")

        if self.type in {"bogo", "b2g1"}:
            buy = 1
            get = 1
            if self.type == "b2g1":
                buy = 2
                get = 1

            group_size = buy + get
            for item in items:
                if not _eligible(item):
                    continue

                qty = int(item.get("quantity") or 0)
                unit_price = _d(item.get("price"))
                if qty <= 0 or unit_price <= 0:
                    continue

                free_qty = (qty // group_size) * get
                if free_qty > 0:
                    discount += unit_price * Decimal(free_qty)

        elif self.type == "combo":
            required_ids = [str(x) for x in (self.target_items or []) if x is not None]
            combo_price = _d(self.value)

            if not required_ids or combo_price <= 0:
                discount = Decimal("0")
            else:
                required_counts = {}
                for rid in required_ids:
                    required_counts[rid] = required_counts.get(rid, 0) + 1

                qty_by_id = {}
                min_price_by_id = {}
                for item in items:
                    item_id = str(item.get("id") or "")
                    if item_id in required_counts:
                        qty_by_id[item_id] = qty_by_id.get(item_id, 0) + int(
                            item.get("quantity") or 0
                        )
                        p = _d(item.get("price"))
                        if item_id not in min_price_by_id:
                            min_price_by_id[item_id] = p
                        else:
                            min_price_by_id[item_id] = min(min_price_by_id[item_id], p)

                # Determine how many full combos can be applied.
                combos = None
                for rid, need in required_counts.items():
                    have = qty_by_id.get(rid, 0)
                    possible = have // need if need > 0 else 0
                    combos = possible if combos is None else min(combos, possible)

                combos = combos or 0
                if combos > 0:
                    regular_sum = Decimal("0")
                    for rid, need in required_counts.items():
                        regular_sum += _d(min_price_by_id.get(rid)) * Decimal(need)

                    discount_per_combo = regular_sum - combo_price
                    if discount_per_combo > 0:
                        discount = Decimal(combos) * discount_per_combo

        # Clamp to max_discount and order_value.
        discount = max(Decimal("0"), discount)
        discount = min(discount, _d(self.max_discount))
        discount = min(discount, _d(order_value))
        return discount

    @property
    def usage_percentage(self):
        """Get usage percentage"""
        if self.usage_limit == 0:
            return 0
        return (self.used_count / self.usage_limit) * 100

    @property
    def is_expiring_soon(self):
        """Check if promotion is expiring within 7 days"""
        if self.status != "active":
            return False
        days_until_expiry = (self.end_date - timezone.now()).days
        return 0 <= days_until_expiry <= 7


class PromotionUsage(models.Model):
    """Track individual usage of promotions"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="usage_records"
    )
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Order where promotion was used",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Customer who used the promotion",
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Actual discount amount applied",
    )
    order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Order value before discount",
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "promotions_discounts_usage"
        verbose_name = "Promotion Usage"
        verbose_name_plural = "Promotion Usages"
        ordering = ["-used_at"]

    def __str__(self):
        return f"{self.promotion.code} - ${self.discount_amount}"
