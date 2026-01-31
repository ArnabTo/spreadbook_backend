from django.db import models
from django.contrib.auth import get_user_model
from utils import random
from utils.models.common_fields import Timestamp
from django.utils.timezone import now

User = get_user_model()


def upload_to(instance, filename):
    return "assets/uploads/company/images/{filename}".format(filename=filename)


class Company(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    phoneNumber = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )
    companyId = models.CharField(max_length=100, default="", blank=True, null=True)
    fullAddress = models.CharField(max_length=200, default="", blank=True, null=True)
    description = models.CharField(max_length=300, default="", blank=True, null=True)
    avatarUrl = models.ImageField(upload_to=upload_to, blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    postedAt = models.DateTimeField(default=now, blank=True, null=True)
    updateAt = models.DateTimeField(auto_now=True)

    # Additional fields to match frontend interface
    logo = models.ImageField(upload_to=upload_to, blank=True, null=True)
    ownerName = models.CharField(
        max_length=200, null=True, blank=True, help_text="Company owner name"
    )
    phone = models.CharField(
        max_length=20, null=True, blank=True, help_text="Alternative phone field"
    )
    address = models.CharField(
        max_length=200, null=True, blank=True, help_text="Alternative address field"
    )
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, default="Bangladesh")
    industry = models.CharField(
        max_length=100,
        choices=[
            ("fine_dining", "Fine Dining"),
            ("fast_food", "Fast Food"),
            ("cafe", "Cafe"),
            ("bar", "Bar"),
            ("cloud_kitchen", "Cloud Kitchen"),
            ("multi_cuisine", "Multi Cuisine"),
        ],
        null=True,
        blank=True,
        help_text="Industry type",
    )
    branch_count_field = models.IntegerField(
        null=True, blank=True, help_text="Number of branches (stored field)"
    )
    activeUsers = models.IntegerField(
        null=True, blank=True, help_text="Number of active users"
    )
    monthlyRevenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly revenue",
    )

    # Subscription fields
    subscriptionPlan = models.CharField(
        max_length=50,
        choices=[
            ("basic", "Basic"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ],
        null=True,
        blank=True,
        help_text="Subscription plan (basic, professional, enterprise)",
    )
    subscriptionStatus = models.CharField(
        max_length=50,
        choices=[
            ("active", "Active"),
            ("trial", "Trial"),
            ("suspended", "Suspended"),
            ("cancelled", "Cancelled"),
            ("payment_overdue", "Payment Overdue"),
            ("pending_approval", "Pending Approval"),
            ("pending_payment", "Pending Payment"),
        ],
        null=True,
        blank=True,
        help_text="Current subscription status",
    )
    subscriptionPrice = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly subscription price",
    )
    lastPaymentDate = models.DateTimeField(
        null=True, blank=True, help_text="Date of last payment"
    )
    nextBillingDate = models.DateTimeField(
        null=True, blank=True, help_text="Next billing date"
    )
    paymentMethod = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Payment method (Credit Card, Bank Transfer, etc.)",
    )
    daysOverdue = models.IntegerField(
        null=True, blank=True, help_text="Number of days payment is overdue"
    )
    trialEndsAt = models.DateTimeField(
        null=True, blank=True, help_text="Trial end date"
    )

    # Reseller fields
    resellerId = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="ID of reseller who sold this company",
    )
    resellerCommission = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Commission percentage for reseller",
    )

    # Approval and Payment Verification fields
    approvalStatus = models.CharField(
        max_length=50,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        null=True,
        blank=True,
        help_text="Approval status",
    )
    approvalDate = models.DateTimeField(
        null=True, blank=True, help_text="Date when company was approved/rejected"
    )
    approvedBy = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Who approved/rejected the company",
    )
    rejectionReason = models.TextField(
        null=True, blank=True, help_text="Reason for rejection"
    )
    paymentType = models.CharField(
        max_length=50,
        choices=[
            ("one_time", "One Time"),
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("yearly", "Yearly"),
        ],
        null=True,
        blank=True,
        help_text="Payment frequency",
    )

    # Initial payment fields
    initialPaymentAmount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Initial payment amount",
    )
    initialPaymentStatus = models.CharField(
        max_length=50,
        choices=[
            ("pending", "Pending"),
            ("verified", "Verified"),
            ("failed", "Failed"),
        ],
        null=True,
        blank=True,
        help_text="Initial payment verification status",
    )
    initialPaymentDate = models.DateTimeField(
        null=True, blank=True, help_text="Date of initial payment"
    )
    initialPaymentMethod = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Method used for initial payment",
    )
    initialPaymentTransactionId = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Transaction ID for initial payment",
    )

    # Setup fee fields
    setupFee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Setup fee amount",
    )
    setupFeeStatus = models.CharField(
        max_length=50,
        choices=[("pending", "Pending"), ("paid", "Paid"), ("waived", "Waived")],
        null=True,
        blank=True,
        help_text="Setup fee payment status",
    )

    # Activity fields
    createdAt = models.DateTimeField(default=now, editable=False)
    lastActive = models.DateTimeField(
        null=True, blank=True, help_text="Last activity timestamp"
    )

    # Features field - JSON field to store enabled features list
    features = models.JSONField(
        default=list,
        blank=True,
        help_text="List of enabled features (e.g., ['pos', 'inventory', 'booking'])",
    )

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["-postedAt"]

    def __str__(self):
        return self.name or "Unnamed Company"

    @property
    def branch_count(self):
        """Get number of branches for this company"""
        return self.company_branches.filter(is_active=True).count()

    @property
    def branches(self):
        """Get stored branch count for API compatibility"""
        return self.branch_count_field or 0


class Branch(models.Model):
    """Shop branch model for multi-location management"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="company_branches",
        help_text="Company this branch belongs to",
    )
    name = models.CharField(
        max_length=100, help_text="Branch name (e.g., Downtown Branch, Mall Location)"
    )
    code = models.CharField(
        max_length=20, unique=True, help_text="Unique branch code (e.g., DT001, ML002)"
    )

    # Contact Information
    phoneNumber = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(
        max_length=20, blank=True, null=True, help_text="Alternative phone field"
    )
    email = models.EmailField(blank=True, null=True)

    # Address Information
    fullAddress = models.CharField(max_length=200, help_text="Street address")
    location = models.CharField(
        max_length=200, blank=True, null=True, help_text="Frontend location field"
    )
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default="Bangladesh")
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # Management
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="managed_branches",
        help_text="Branch manager",
    )
    manager_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Manager name (for frontend compatibility)",
    )

    # Restaurant Specific Details
    opening_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text="Opening hours for each day (e.g., {'monday': '9:00-22:00'})",
    )
    openingHours = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Opening hours string for frontend",
    )
    seating_capacity = models.PositiveIntegerField(
        default=0, help_text="Total seating capacity"
    )
    delivery_radius = models.FloatField(
        default=0.0, help_text="Delivery radius in kilometers"
    )

    # Sales and Operational Data (for dashboard metrics)
    todaySales = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text="Today's sales amount"
    )
    monthSales = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text="Current month's sales"
    )
    activeOrders = models.PositiveIntegerField(
        default=0, help_text="Number of active orders"
    )
    activeTables = models.PositiveIntegerField(
        default=0, help_text="Number of active/occupied tables"
    )
    staff = models.PositiveIntegerField(default=0, help_text="Number of staff members")

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        default="active",
        help_text="Branch status for frontend compatibility",
    )
    is_active = models.BooleanField(default=True)
    postedAt = models.DateTimeField(default=now, editable=False)
    updateAt = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        ordering = ["company", "name"]
        unique_together = ["company", "code"]

    def __str__(self):
        return f"{self.company.name} - {self.name}"

    @property
    def full_address(self):
        """Get formatted full address"""
        address_parts = [self.fullAddress]
        if self.city:
            address_parts.append(self.city)
        if self.state:
            address_parts.append(self.state)
        if self.postal_code:
            address_parts.append(self.postal_code)
        address_parts.append(self.country)
        return ", ".join(filter(None, address_parts))

    @property
    def user_count(self):
        """Get number of users assigned to this branch"""
        try:
            from utils.sqlite_compat import filter_users_by_branch_access

            users = filter_users_by_branch_access(
                User.objects, [self.id], check_active=True
            )
            return len(users) if isinstance(users, list) else users.count()
        except Exception:
            # Fallback to 0 if there's any error
            return 0

    @property
    def companyId(self):
        """Get company ID as string for frontend compatibility"""
        return str(self.company.id) if self.company else None

    def save(self, *args, **kwargs):
        # Auto-generate code if not provided
        if not self.code and self.company:
            company_prefix = (self.company.name or "BR")[:2].upper()
            branch_count = Branch.objects.filter(company=self.company).count() + 1
            self.code = f"{company_prefix}{branch_count:03d}"

        # Sync status fields
        if self.is_active:
            self.status = "active"
        else:
            self.status = "inactive"

        # Auto-populate location from fullAddress if not provided
        if not self.location and self.fullAddress:
            self.location = self.fullAddress

        # Auto-populate manager_name from manager if not provided
        if not self.manager_name and self.manager:
            self.manager_name = self.manager.get_full_name() or self.manager.username

        # Auto-populate phone from phoneNumber if not provided
        if not self.phone and self.phoneNumber:
            self.phone = self.phoneNumber

        super().save(*args, **kwargs)


class CompanyCustomization(models.Model):
    """Customization settings for companies"""

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="customization",
        help_text="Company these customizations belong to",
    )
    primaryColor = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        help_text="Primary color in hex format (e.g., #8B4513)",
    )
    currency = models.CharField(
        max_length=3,
        null=True,
        blank=True,
        help_text="Currency code (e.g., USD, EUR, GBP)",
    )
    taxRate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tax rate percentage",
    )
    timezone = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Timezone (e.g., America/New_York)",
    )

    # Pharmacy / prescription workflow
    enforce_prescriptions = models.BooleanField(
        default=False,
        help_text=(
            "If enabled, prescription-required products cannot be sold unless an approved prescription is attached."
        ),
    )
    enforce_controlled_substances = models.BooleanField(
        default=False,
        help_text="If enabled, controlled substances additionally require an approved prescription.",
    )

    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Customization"
        verbose_name_plural = "Company Customizations"
        ordering = ["company"]

    def __str__(self):
        return f"{self.company.name} - Customization"
