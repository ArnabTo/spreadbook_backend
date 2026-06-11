from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from utils.models.common_fields import Timestamp
import uuid


def upload_to_customer(instance, filename):
    return "assets/uploads/customer/{filename}".format(filename=filename)


def upload_to_customer_attachment(instance, filename):
    return "assets/uploads/customer/attachments/{filename}".format(filename=filename)


TYPE_CHOICE = (
    ("Home", "Home"),
    ("Office", "Office"),
    ("Wirehouse", "Wirehouse"),
    ("Other", "Other"),
)

ALLOWED_ATTACHMENT_EXTENSIONS = ["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"]


class Customer(Timestamp):
    """
    Enhanced Customer model with accounting, bilingual address, and attachment fields
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

    # Party Info fields
    name = models.CharField(
        db_index=True,
        max_length=200,
        verbose_name=_("Customer Name"),
        blank=True,
        null=True,
    )
    display_name = models.CharField(
        max_length=200,
        verbose_name=_("Display Name"),
        blank=True,
        null=True,
    )
    arabic_name = models.CharField(
        max_length=200,
        verbose_name=_("Arabic Name"),
        blank=True,
        null=True,
    )
    address = models.TextField(
        max_length=500, verbose_name=_("Address"), blank=True, null=True
    )
    arabic_address = models.TextField(
        max_length=500, verbose_name=_("Arabic Address"), blank=True, null=True
    )

    # Code — unique per company enforced at serializer/view level
    customer_code = models.CharField(
        max_length=50,
        verbose_name=_("Customer Code"),
        db_index=True,
        blank=True,
        null=True,
        help_text=_("Auto-generated customer code (e.g., CUST001)"),
    )
    phoneNumber = models.CharField(
        max_length=100, verbose_name=_("Phone Number"), blank=True, null=True
    )
    mobile_number = models.CharField(
        max_length=20, verbose_name=_("Mobile Number"), blank=True, null=True
    )
    email = models.EmailField(
        db_index=True, verbose_name=_("Email Address"), blank=True, null=True
    )

    # Accounting & compliance
    vat_no = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("VAT No"))
    cr_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("CR Number"))
    is_effected_to_ledger = models.BooleanField(default=True, verbose_name=_("Is Effected To Ledger"))
    credit_period = models.PositiveIntegerField(
        default=0, verbose_name=_("Credit Period"), help_text=_("Number Of Days"), blank=True, null=True
    )
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name=_("Credit Limit"), blank=True, null=True
    )
    opening_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name=_("Opening Balance"), blank=True, null=True
    )

    # Contact & Sales
    contact_person = models.CharField(
        max_length=100, verbose_name=_("Contact Person"), blank=True, null=True
    )
    sales_person = models.ForeignKey(
        "authenticator.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_customers",
        verbose_name=_("Sales Person"),
    )

    # Classification
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

    # Business metrics
    totalOrders = models.PositiveIntegerField(
        default=0, verbose_name=_("Total Orders")
    )
    totalSpent = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name=_("Total Amount Spent")
    )
    loyaltyPoints = models.PositiveIntegerField(
        default=0, verbose_name=_("Loyalty Points")
    )
    lastVisit = models.DateField(
        auto_now_add=True, verbose_name=_("Last Visit Date")
    )

    # ── Bilingual Address Fields (Warehouse-style) ──
    country_ref = models.ForeignKey(
        "company.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_countries",
    )
    arabic_country = models.CharField(max_length=100, blank=True, null=True)
    state_ref = models.ForeignKey(
        "company.StateProvince",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_states",
    )
    arabic_state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, default="", blank=True, null=True)
    arabic_city = models.CharField(max_length=100, blank=True, null=True)
    building_no = models.CharField(max_length=50, blank=True, null=True)
    arabic_building_no = models.CharField(max_length=50, blank=True, null=True)
    street_name = models.CharField(max_length=200, blank=True, null=True)
    arabic_street_name = models.CharField(max_length=200, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    arabic_district = models.CharField(max_length=100, blank=True, null=True)
    additional_no = models.CharField(max_length=50, blank=True, null=True)
    arabic_additional_no = models.CharField(max_length=50, blank=True, null=True)
    zip_code = models.CharField(max_length=200, blank=True, null=True)
    arabic_zip_code = models.CharField(max_length=20, blank=True, null=True)

    # Legacy compat
    fullAddress = models.TextField(
        max_length=500, verbose_name=_("Full Address"), blank=True, null=True
    )
    addressType = models.CharField(
        max_length=100, choices=TYPE_CHOICE, default="Home", blank=True, null=True
    )
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
    notes = models.TextField(
        max_length=1000, blank=True, null=True, verbose_name=_("Customer Notes")
    )
    othercompany = models.CharField(max_length=100, default="", blank=True, null=True)

    def get_customer_url(self):
        return reverse("customer_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("update_customer", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("delete_customer", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if self.is_effected_to_ledger is not True:
            self.is_effected_to_ledger = True
        super().save(*args, **kwargs)

    def __str__(self):
        if self.name and self.customer_code:
            return f"{self.name} ({self.customer_code})"
        elif self.name:
            return f"{self.name} ({self.category})"
        elif self.customer_code:
            return f"Customer {self.customer_code}"
        return f"Customer {self.id}"

    @property
    def is_active(self):
        return self.status == "Active"

    @property
    def is_vip(self):
        return self.category == "vip"

    def add_loyalty_points(self, points):
        self.loyaltyPoints += points
        self.save(update_fields=["loyaltyPoints"])

    def update_total_spent(self, amount):
        self.totalSpent += amount
        self.totalOrders += 1
        points_earned = int(amount / 100)
        self.loyaltyPoints += points_earned
        self.save(update_fields=["totalSpent", "totalOrders", "loyaltyPoints"])
        return points_earned

    def clean(self):
        super().clean()
        if not self.name and not self.email:
            from django.core.exceptions import ValidationError
            raise ValidationError(_("Customer must have either name or email"))

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        ordering = ["-created_at", "name"]
        indexes = [
            models.Index(fields=["companyId"]),
            models.Index(fields=["customer_code"]),
            models.Index(fields=["name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["mobile_number"]),
            models.Index(fields=["country_ref"]),
            models.Index(fields=["state_ref"]),
            models.Index(fields=["phoneNumber"]),
            models.Index(fields=["category"]),
            models.Index(fields=["status"]),
            models.Index(fields=["lastVisit"]),
            models.Index(fields=["credit_period"]),
            models.Index(fields=["opening_balance"]),
        ]


class CustomerAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Customer"),
    )
    file = models.FileField(
        upload_to=upload_to_customer_attachment,
        verbose_name=_("Attachment File"),
    )
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.PositiveIntegerField(default=0, verbose_name=_("File Size (bytes)"))
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Customer Attachment")
        verbose_name_plural = _("Customer Attachments")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Attachment for {self.customer.name} - {self.original_filename or self.file.name}"
