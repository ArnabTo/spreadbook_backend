from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _


STATUS_CHOICES = (
    ("active", "Active"),
    ("inactive", "Inactive"),
    ("suspended", "Suspended"),
)


class Reseller(models.Model):
    """Reseller model for managing reseller partners"""

    # Basic Information
    name = models.CharField(
        max_length=100,
        verbose_name=_("Reseller Name"),
        help_text="Full name of the reseller",
    )
    companyName = models.CharField(
        max_length=150,
        verbose_name=_("Company Name"),
        help_text="Name of the reseller's company",
    )
    email = models.EmailField(
        unique=True,
        verbose_name=_("Email Address"),
        help_text="Primary email address for communication",
    )

    # Contact Information
    phone_regex = RegexValidator(
        regex=r"^(?:\+88|88)?(01[3-9]\d{8})$",
        message="Phone number must be entered in the format: '+8801XXXXXX'. Up to 14 digits allowed.",
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=20,
        verbose_name=_("Phone Number"),
        help_text="Contact phone number",
    )

    # Address Information
    address = models.TextField(
        verbose_name=_("Address"), help_text="Complete address of the reseller"
    )
    city = models.CharField(
        max_length=100,
        verbose_name=_("City"),
        help_text="City where reseller is located",
    )
    country = models.CharField(
        max_length=100,
        verbose_name=_("Country"),
        help_text="Country where reseller operates",
    )

    # Business Information
    defaultCommission = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Default Commission (%)"),
        help_text="Default commission percentage for this reseller",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        verbose_name=_("Status"),
        help_text="Current status of the reseller",
    )

    # Statistics (computed fields)
    totalClients = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Clients"),
        help_text="Total number of clients managed by this reseller",
    )
    totalRevenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Total Revenue"),
        help_text="Total revenue generated from all clients",
    )
    commissionEarned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Commission Earned"),
        help_text="Total commission earned by this reseller",
    )

    # Timestamps
    joinedDate = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Joined Date"),
        help_text="Date when reseller joined the platform",
    )
    lastActive = models.DateTimeField(
        auto_now=timezone.now,
        verbose_name=_("Last Active"),
        help_text="Last time reseller was active",
    )

    # Additional timestamps
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = "Reseller"
        verbose_name_plural = "Resellers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["status"]),
            models.Index(fields=["joinedDate"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.companyName})"

    def save(self, *args, **kwargs):
        # Update lastActive whenever the model is saved
        self.lastActive = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        """Check if reseller is active"""
        return self.status == "active"

    @property
    def commission_rate_display(self):
        """Display commission rate as percentage"""
        return f"{self.defaultCommission}%"

    def calculate_commission(self, revenue_amount):
        """Calculate commission for a given revenue amount"""
        return (revenue_amount * self.defaultCommission) / 100

    def update_statistics(self):
        """Update reseller statistics from related data"""
        # This method can be called to recalculate statistics
        # You'll need to implement the actual calculation based on your business logic
        # For now, this is a placeholder for the method
        pass


class ResellerCommission(models.Model):
    """Model to track individual commission records for resellers"""

    reseller = models.ForeignKey(
        Reseller,
        on_delete=models.CASCADE,
        related_name="commissions",
        verbose_name=_("Reseller"),
    )
    client_company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        verbose_name=_("Client Company"),
        help_text="Company that generated this commission",
    )
    revenue_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Revenue Amount"),
        help_text="Amount of revenue that generated this commission",
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_("Commission Rate (%)"),
        help_text="Commission rate applied for this transaction",
    )
    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Commission Amount"),
        help_text="Actual commission amount earned",
    )

    # Status and payment tracking
    is_paid = models.BooleanField(
        default=False,
        verbose_name=_("Is Paid"),
        help_text="Whether this commission has been paid",
    )
    paid_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Paid Date"),
        help_text="Date when commission was paid",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = "Reseller Commission"
        verbose_name_plural = "Reseller Commissions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reseller", "is_paid"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Commission for {self.reseller.name} - {self.commission_amount}"

    def save(self, *args, **kwargs):
        # Auto-calculate commission amount if not provided
        if not self.commission_amount:
            self.commission_amount = (self.revenue_amount * self.commission_rate) / 100
        super().save(*args, **kwargs)
