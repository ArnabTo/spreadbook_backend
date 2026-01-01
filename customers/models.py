from django.db import models
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from utils.models.common_fields import Timestamp
import uuid


def upload_to_customer(instance, filename):
    return "assets/uploads/customer/{filename}".format(filename=filename)


TYPE_CHOICE = (
    ("Home", "Home"),
    ("Office", "Office"),
    ("Wirehouse", "Wirehouse"),
    ("Other", "Other"),
)


class Customer(Timestamp):
    """
    Enhanced Customer model for restaurant management
    """

    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Suspended", "Suspended"),
    ]

    CATEGORY_CHOICES = [
        ("regular", "Regular"),
        ("vip", "VIP"),
        ("corporate", "Corporate"),
        ("consulate", "Consulate"),
    ]

    GENDER_SELECT = (
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    )

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
    name = models.CharField(
        db_index=True,
        max_length=200,
        verbose_name=_("Customer Name"),
        blank=True,
        null=True,
    )
    customer_code = models.CharField(
        max_length=50,
        verbose_name=_("Customer Code"),
        unique=True,
        blank=True,
        null=True,
        help_text=_("Auto-generated customer code (e.g., CUST001)"),
    )
    email = models.EmailField(verbose_name=_("Email Address"), blank=True, null=True)
    phoneNumber = models.CharField(
        max_length=100, verbose_name=_("Phone Number"), blank=True, null=True
    )

    # Enhanced fields for frontend compatibility
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="regular",
        verbose_name=_("Customer Category"),
        help_text=_("Customer type classification"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Active",
        verbose_name=_("Customer Status"),
    )

    # Business fields
    totalOrders = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Orders"),
        help_text=_("Total number of orders placed by customer"),
    )

    totalSpent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Total Amount Spent"),
        help_text=_("Total amount spent by customer"),
    )

    loyaltyPoints = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Loyalty Points"),
        help_text=_("Accumulated loyalty points"),
    )

    lastVisit = models.DateField(
        auto_now_add=True,
        verbose_name=_("Last Visit Date"),
        help_text=_("Date of customer's last visit"),
    )

    # Address and contact details
    fullAddress = models.TextField(
        max_length=500, verbose_name=_("Full Address"), blank=True, null=True
    )
    addressType = models.CharField(
        max_length=100, choices=TYPE_CHOICE, default="Home", blank=True, null=True
    )
    city = models.CharField(max_length=100, default="", blank=True, null=True)
    zip_code = models.CharField(max_length=200, blank=True, null=True)

    # Legacy fields (maintain compatibility)
    gender = models.CharField(
        max_length=200, choices=GENDER_SELECT, default="Other", blank=True, null=True
    )
    company = models.CharField(max_length=100, default="", blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    primary = models.BooleanField(default=False, blank=True, null=True)
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, null=True
    )
    previous_balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, null=True
    )
    avatarUrl = models.ImageField(upload_to=upload_to_customer, blank=True, null=True)

    # Special preferences and notes
    notes = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Customer Notes"),
        help_text=_("Special preferences, allergies, etc."),
    )

    othercompany = models.CharField(max_length=100, default="", blank=True, null=True)

    def get_customer_url(self):
        return reverse("customer_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("update_customer", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("delete_customer", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        """
        Converts a string into all uppercase.
        eg: if customer name is "sakib", then it will save as "Sakib"
        """
        self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        """String for representing the Model object."""
        if self.name and self.customer_code:
            return f"{self.name} ({self.customer_code})"
        elif self.name:
            return f"{self.name} ({self.category})"
        elif self.customer_code:
            return f"Customer {self.customer_code}"
        else:
            return f"Customer {self.id}"

    @property
    def is_active(self):
        """Check if customer is active"""
        return self.status == "Active"

    @property
    def is_vip(self):
        """Check if customer is VIP"""
        return self.category == "vip"

    def add_loyalty_points(self, points):
        """Add loyalty points to customer"""
        self.loyaltyPoints += points
        self.save(update_fields=["loyaltyPoints"])

    def update_total_spent(self, amount):
        """Update total spent amount and increment order count"""
        self.totalSpent += amount
        self.totalOrders += 1
        # Award loyalty points (1 point per 100 BDT spent)
        points_earned = int(amount / 100)
        self.loyaltyPoints += points_earned
        self.save(update_fields=["totalSpent", "totalOrders", "loyaltyPoints"])
        return points_earned  # Return points earned for notification

    def clean(self):
        """Validate model fields"""
        super().clean()
        if not self.name and not self.email:
            from django.core.exceptions import ValidationError

            raise ValidationError(_("Customer must have either name or email"))

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        ordering = ["-created_at", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["customer_code"]),
            models.Index(fields=["phoneNumber"]),
            models.Index(fields=["email"]),
            models.Index(fields=["category"]),
            models.Index(fields=["status"]),
            models.Index(fields=["lastVisit"]),
        ]
