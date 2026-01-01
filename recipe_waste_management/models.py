from django.db import models
from django.conf import settings
from company.models import Company, Branch
import uuid
from decimal import Decimal


class Recipe(models.Model):
    """Recipe model for recipe costing and management"""

    CATEGORY_CHOICES = [
        ("appetizer", "Appetizer"),
        ("main_course", "Main Course"),
        ("dessert", "Dessert"),
        ("beverage", "Beverage"),
        ("thai", "Thai"),
        ("kebab", "Kebab"),
        ("indian", "Indian"),
        ("chinese", "Chinese"),
        ("continental", "Continental"),
        ("seafood", "Seafood"),
        ("vegetarian", "Vegetarian"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dish_name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default="other"
    )
    serving_size = models.PositiveIntegerField(default=1)
    prep_time = models.PositiveIntegerField(help_text="Preparation time in minutes")
    cook_time = models.PositiveIntegerField(help_text="Cooking time in minutes")
    instructions = models.TextField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    profit_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Profit margin percentage",
    )

    # Business relationships
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="recipes", null=True, blank=True
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, null=True, blank=True, related_name="recipes"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_recipes",
        null=True,
        blank=True,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"

    def __str__(self):
        return f"{self.dish_name} ({self.category})"

    def save(self, *args, **kwargs):
        """Auto-calculate total cost and profit margin"""
        # Calculate total cost from ingredients
        if self.pk:
            total_ingredient_cost = sum(
                [ingredient.cost for ingredient in self.ingredients.all()]
            )
            self.total_cost = total_ingredient_cost

        # Calculate profit margin
        if self.selling_price > 0 and self.total_cost > 0:
            self.profit_margin = (
                (self.selling_price - self.total_cost) / self.selling_price
            ) * 100

        super().save(*args, **kwargs)


class RecipeIngredient(models.Model):
    """Individual ingredient in a recipe"""

    UNIT_CHOICES = [
        ("g", "Grams"),
        ("kg", "Kilograms"),
        ("ml", "Milliliters"),
        ("l", "Liters"),
        ("pcs", "Pieces"),
        ("cups", "Cups"),
        ("tbsp", "Tablespoons"),
        ("tsp", "Teaspoons"),
        ("oz", "Ounces"),
        ("lb", "Pounds"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="ingredients"
    )
    name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Cost for this quantity"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.name}"


class WasteRecord(models.Model):
    """Food waste tracking model"""

    REASON_CHOICES = [
        ("expired", "Expired"),
        ("spoiled", "Spoiled"),
        ("overproduction", "Overproduction"),
        ("damaged", "Damaged"),
        ("other", "Other"),
    ]

    UNIT_CHOICES = [
        ("kg", "Kilograms"),
        ("g", "Grams"),
        ("liters", "Liters"),
        ("pcs", "Pieces"),
        ("servings", "Servings"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    item_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Financial loss from waste"
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    notes = models.TextField(blank=True, help_text="Additional details about the waste")

    # Business relationships
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="waste_records"
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="waste_records",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recorded_waste",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Waste Record"
        verbose_name_plural = "Waste Records"

    def __str__(self):
        return f"{self.item_name} - {self.quantity} {self.unit} ({self.date})"
