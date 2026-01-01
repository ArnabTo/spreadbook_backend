from django.db import models
from django.core.validators import MinValueValidator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from utils.models.common_fields import Timestamp
import uuid


class MenuCategory(models.Model):
    """
    Menu categories for organizing menu items
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Category Name"),
        help_text=_("Name of the menu category"),
    )

    # Multi-tenant scoping
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Category Description"),
        help_text=_("Description of this menu category"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether this category is active"),
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order in which categories are displayed"),
    )

    class Meta:
        verbose_name = _("Menu Category")
        verbose_name_plural = _("Menu Categories")
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class MenuItem(Timestamp):
    """
    Menu item model for restaurant menu management
    """

    AVAILABILITY_CHOICES = [
        (True, _("Available")),
        (False, _("Unavailable")),
    ]

    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenant scoping
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    item_code = models.CharField(
        max_length=50,
        verbose_name=_("Item Code"),
        unique=True,
        blank=True,
        null=True,
        help_text=_("Auto-generated item code (e.g., ITEM001)"),
    )

    name = models.CharField(
        max_length=200,
        verbose_name=_("Menu Item Name"),
        db_index=True,
        help_text=_("Name of the menu item"),
    )

    category = models.CharField(
        max_length=100,
        verbose_name=_("Category"),
        db_index=True,
        default="General",
        help_text=_("Category of the menu item"),
    )

    # Pricing fields
    price = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name=_("Selling Price"),
        help_text=_("Selling price of the menu item in BDT"),
    )

    cost = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name=_("Cost Price"),
        help_text=_("Cost price of the menu item in BDT"),
    )

    # Description and details
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description of the menu item"),
    )

    short_description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Short Description"),
        help_text=_("Brief description for display purposes"),
    )

    # Availability and status
    available = models.BooleanField(
        default=True,
        verbose_name=_("Available"),
        db_index=True,
        help_text=_("Whether this item is available for ordering"),
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name=_("Featured Item"),
        help_text=_("Whether this item is featured on the menu"),
    )

    # Nutritional and additional info
    preparation_time = models.PositiveIntegerField(
        default=15,
        verbose_name=_("Preparation Time"),
        help_text=_("Estimated preparation time in minutes"),
    )

    calories = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Calories"),
        help_text=_("Estimated calories per serving"),
    )

    # Ingredients and dietary info
    ingredients = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Ingredients"),
        help_text=_("List of ingredients used in this item"),
    )

    is_vegetarian = models.BooleanField(
        default=False,
        verbose_name=_("Vegetarian"),
        help_text=_("Whether this item is vegetarian"),
    )

    is_vegan = models.BooleanField(
        default=False,
        verbose_name=_("Vegan"),
        help_text=_("Whether this item is vegan"),
    )

    contains_gluten = models.BooleanField(
        default=False,
        verbose_name=_("Contains Gluten"),
        help_text=_("Whether this item contains gluten"),
    )

    # Business metrics
    total_sold = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Sold"),
        help_text=_("Total number of times this item has been sold"),
    )

    total_revenue = models.FloatField(
        default=0,
        verbose_name=_("Total Revenue"),
        help_text=_("Total revenue generated from this item"),
    )

    # Display and sorting
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Order in which items are displayed in the category"),
    )

    # Image field (optional)
    image = models.ImageField(
        upload_to="menu_items/",
        blank=True,
        null=True,
        verbose_name=_("Item Image"),
        help_text=_("Image of the menu item"),
    )

    @property
    def profit(self):
        """Calculate profit per item"""
        if self.price is not None and self.cost is not None:
            return self.price - self.cost
        return 0.0

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.price is not None and self.cost is not None and self.price > 0:
            return ((self.price - self.cost) / self.price) * 100
        return 0.0

    @property
    def markup_percentage(self):
        """Calculate markup percentage"""
        if self.price is not None and self.cost is not None and self.cost > 0:
            return ((self.price - self.cost) / self.cost) * 100
        return 0.0

    def update_sales_metrics(self, quantity_sold):
        """Update sales metrics when item is sold"""
        if quantity_sold > 0 and self.price is not None:
            self.total_sold += quantity_sold
            self.total_revenue += self.price * quantity_sold
            self.save(update_fields=["total_sold", "total_revenue", "updated_at"])

    def get_absolute_url(self):
        return reverse("menu_item_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("update_menu_item", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("delete_menu_item", kwargs={"pk": self.pk})

    def clean(self):
        """Validate model fields"""
        super().clean()
        from django.core.exceptions import ValidationError

        # Only validate price vs cost if both values are provided
        if self.cost is not None and self.price is not None and self.cost >= self.price:
            raise ValidationError(_("Cost price should be less than selling price"))

        if not self.name:
            raise ValidationError(_("Menu item name is required"))

    def save(self, *args, **kwargs):
        """Override save to generate item_code if not provided"""
        if not self.item_code:
            # Generate item code like ITEM001, ITEM002, etc.
            last_item = MenuItem.objects.all().order_by("item_code").last()

            if (
                last_item
                and last_item.item_code
                and last_item.item_code.startswith("ITEM")
            ):
                try:
                    last_num = int(last_item.item_code[4:])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            self.item_code = f"ITEM{new_num:03d}"

        # Convert name to title case
        if self.name:
            self.name = self.name.title()

        super().save(*args, **kwargs)

    def __str__(self):
        """String representation of menu item"""
        if self.item_code:
            return f"{self.name} ({self.item_code})"
        return f"{self.name} - {self.category}"

    class Meta:
        verbose_name = _("Menu Item")
        verbose_name_plural = _("Menu Items")
        ordering = ["-created_at", "display_order", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["item_code"]),
            models.Index(fields=["category"]),
            models.Index(fields=["available"]),
            models.Index(fields=["price"]),
            models.Index(fields=["cost"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["total_sold"]),
        ]
