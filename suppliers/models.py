from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models.common_fields import Timestamp
import uuid


class SupplierCategory(Timestamp):
    """
    Supplier Category model for storing supplier categories company-wise
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        verbose_name=_("Category Name"),
        help_text=_("Name of the supplier category"),
    )
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="supplier_categories",
        verbose_name=_("Company"),
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Optional description for this category"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether this category is currently active"),
    )

    class Meta:
        verbose_name = _("Supplier Category")
        verbose_name_plural = _("Supplier Categories")
        ordering = ["name"]
        unique_together = [["name", "companyId"]]
        indexes = [
            models.Index(fields=["companyId", "is_active"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return (
            f"{self.name} ({self.companyId.name if self.companyId else 'No Company'})"
        )


class Supplier(Timestamp):
    """
    Supplier model for storing supplier data🛢
    """

    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Suspended", "Suspended"),
    ]

    PAYMENT_TERMS_CHOICES = [
        ("Net 15", "Net 15"),
        ("Net 20", "Net 20"),
        ("Net 30", "Net 30"),
        ("COD", "Cash on Delivery"),
        ("Advance", "Advance Payment"),
    ]

    # Core fields from original model
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100, verbose_name=_("Supplier Full Name"), null=True, blank=True
    )

    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    branchId = models.ManyToManyField(
        "company.Branch",
        blank=True,
        help_text="Branches this user can access",
    )

    supplier_code = models.CharField(
        max_length=50, verbose_name=_("Supplier Code"), null=True, blank=True
    )
    address = models.CharField(
        max_length=200, verbose_name=_("Supplier Address"), null=True, blank=True
    )
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.CharField(
        max_length=100, verbose_name=_("Supplier Email"), null=True, blank=True
    )
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=100, default="BD", null=True, blank=True)
    fax = models.CharField(
        max_length=20, null=True, blank=True, verbose_name=_("Supplier Fax")
    )
    previous_balance = models.FloatField(
        default=0,
        verbose_name=_("Supplier Previous Balance"),
        null=True,
        blank=True,
    )

    # Additional frontend-specific fields
    category = models.ForeignKey(
        SupplierCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suppliers",
        verbose_name=_("Supplier Category"),
        help_text=_("Category of this supplier"),
    )

    image = models.ImageField(
        upload_to="supplier_images/",
        null=True,
        blank=True,
        verbose_name=_("Supplier Image"),
        help_text=_("Profile image or logo of the supplier"),
    )

    contactPerson = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Contact Person Name")
    )

    rating = models.FloatField(
        default=0.0,
        verbose_name=_("Supplier Rating"),
        help_text=_("Rating from 0.0 to 5.0"),
        null=True,
        blank=True,
    )

    totalPurchases = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Number of Purchases"),
        help_text=_("Total number of purchase orders from this supplier"),
        null=True,
        blank=True,
    )

    totalSpent = models.FloatField(
        default=0,
        verbose_name=_("Total Amount Spent"),
        help_text=_("Total amount spent on purchases from this supplier"),
        null=True,
        blank=True,
    )

    paymentTerms = models.CharField(
        max_length=20,
        choices=PAYMENT_TERMS_CHOICES,
        default="Net 30",
        verbose_name=_("Payment Terms"),
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Active",
        verbose_name=_("Supplier Status"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ["-created_at", "name"]
        indexes = [
            models.Index(fields=["supplier_code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["companyId"]),
        ]

    def __str__(self):
        """String for representing the Model object."""
        return f"{self.name} ({self.supplier_code})"

    def clean(self):
        """Validate model fields"""
        super().clean()
        if self.rating and (self.rating < 0 or self.rating > 5):
            from django.core.exceptions import ValidationError

            raise ValidationError(_("Rating must be between 0.0 and 5.0"))

    @property
    def is_active(self):
        """Check if supplier is active"""
        return self.status == "Active"

    def update_total_spent(self, amount):
        """Update total spent amount"""
        self.totalSpent += amount
        self.save(update_fields=["totalSpent"])

    def increment_purchase_count(self):
        """Increment total purchase count"""
        self.totalPurchases += 1
        self.save(update_fields=["totalPurchases"])
