from django.db import models
from django.contrib.auth import get_user_model
from utils import random
from utils.models.common_fields import Timestamp
from django.utils.timezone import now
from django.utils.text import slugify

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
    company_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique company code used for imports and branch code generation.",
    )
    fullAddress = models.CharField(max_length=200, default="", blank=True, null=True)
    description = models.CharField(max_length=300, default="", blank=True, null=True)
    avatarUrl = models.ImageField(upload_to=upload_to, blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    postedAt = models.DateTimeField(default=now, blank=True, null=True)
    updateAt = models.DateTimeField(auto_now=True)

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
            ("demo", "Demo"),
            ("basic", "Basic"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ],
        null=True,
        blank=True,
        help_text="Subscription plan (demo, basic, professional, enterprise)",
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

    # Receipt header fields
    company_title_line1 = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="First subtitle line for receipt header",
    )
    company_title_line2 = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Second subtitle line for receipt header",
    )
    company_website = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Company website for receipt header",
    )

    # Saudi-specific - bilingual Commercial Registration number
    cr_number_en = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Commercial Registration Number (English)",
    )
    cr_number_ar = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="رقم السجل التجاري (Arabic)",
    )

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["-postedAt"]

    def __str__(self):
        return self.name or "Unnamed Company"

    @staticmethod
    def _base_company_code(name):
        normalized = slugify(name or "").upper().replace("-", "")
        if not normalized:
            return "CMP"
        return normalized[:6]

    def save(self, *args, **kwargs):
        if not self.company_code:
            base_code = self._base_company_code(self.name)
            candidate = base_code
            serial = 1
            while (
                Company.objects.exclude(pk=self.pk)
                .filter(company_code__iexact=candidate)
                .exists()
            ):
                serial += 1
                candidate = f"{base_code}{serial:02d}"[:20]
            self.company_code = candidate
        super().save(*args, **kwargs)

    @property
    def branch_count(self):
        return self.company_branches.filter(is_active=True).count()

    @property
    def branches(self):
        return self.branch_count_field or 0


class Branch(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="company_branches",
        help_text="Company this branch belongs to",
    )
    warehouse = models.ForeignKey(
        "Warehouse",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="warehouse_branches",
        help_text="Warehouse this branch belongs to",
    )
    name = models.CharField(
        max_length=100, help_text="Branch name"
    )
    code = models.CharField(
        max_length=20, unique=True, help_text="Unique branch code"
    )

    phoneNumber = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(
        max_length=20, blank=True, null=True, help_text="Alternative phone field"
    )
    email = models.EmailField(blank=True, null=True)

    fullAddress = models.CharField(max_length=200, help_text="Street address")
    location = models.CharField(
        max_length=200, blank=True, null=True, help_text="Frontend location field"
    )
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default="Bangladesh")
    postal_code = models.CharField(max_length=20, blank=True, null=True)

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

    opening_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text="Opening hours for each day",
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
        try:
            from utils.sqlite_compat import filter_users_by_branch_access
            users = filter_users_by_branch_access(
                User.objects, [self.id], check_active=True
            )
            return len(users) if isinstance(users, list) else users.count()
        except Exception:
            return 0

    @property
    def companyId(self):
        return str(self.company.id) if self.company else None

    def save(self, *args, **kwargs):
        if not self.code and self.company:
            company_prefix = "".join(
                char
                for char in str(
                    self.company.company_code or self.company.companyId or "CMP"
                ).upper()
                if char.isalnum()
            )[:8]
            if not company_prefix:
                company_prefix = "CMP"

            branch_count = (
                Branch.objects.filter(company=self.company).exclude(pk=self.pk).count()
            ) + 1

            while True:
                candidate_code = f"{company_prefix}-BR{branch_count:03d}"
                if (
                    not Branch.objects.exclude(pk=self.pk)
                    .filter(code__iexact=candidate_code)
                    .exists()
                ):
                    self.code = candidate_code
                    break
                branch_count += 1

        if self.is_active:
            self.status = "active"
        else:
            self.status = "inactive"

        if not self.location and self.fullAddress:
            self.location = self.fullAddress

        if not self.manager_name and self.manager:
            self.manager_name = self.manager.get_full_name() or self.manager.username

        if not self.phone and self.phoneNumber:
            self.phone = self.phoneNumber

        super().save(*args, **kwargs)


class Warehouse(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="company_warehouses",
        help_text="Company this warehouse belongs to",
    )
    parent_warehouse = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="child_warehouses",
        help_text="Parent warehouse",
    )

    name = models.CharField(max_length=100, help_text="Warehouse name")
    code = models.CharField(
        max_length=20, unique=True, help_text="Unique warehouse code"
    )

    phoneNumber = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    fullAddress = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default="Bangladesh")
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="managed_warehouses",
        help_text="Warehouse manager",
    )
    manager_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Manager name (for frontend compatibility)",
    )

    capacity = models.PositiveIntegerField(
        default=0, help_text="Total storage capacity (units)"
    )
    warehouseType = models.CharField(
        max_length=50,
        choices=[
            ("main", "Main Warehouse"),
            ("regional", "Regional Warehouse"),
            ("distribution", "Distribution Center"),
            ("cold_storage", "Cold Storage"),
            ("transit", "Transit Warehouse"),
        ],
        default="main",
        help_text="Type of warehouse",
    )

    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )

    postedAt = models.DateTimeField(default=now, editable=False)
    updateAt = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
        ordering = ["company", "name"]
        unique_together = ["company", "code"]

    def __str__(self):
        return f"{self.company.name} - {self.name}"

    @property
    def companyId(self):
        return str(self.company.id) if self.company else None

    @property
    def branch_count(self):
        return self.warehouse_branches.filter(is_active=True).count()

    def save(self, *args, **kwargs):
        if not self.code and self.company:
            company_prefix = (self.company.name or "WH")[:2].upper()
            wh_count = Warehouse.objects.filter(company=self.company).count() + 1
            self.code = f"WH{company_prefix}{wh_count:03d}"

        self.status = "active" if self.is_active else "inactive"

        super().save(*args, **kwargs)


class CompanyCustomization(models.Model):
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
        help_text="Primary color in hex format",
    )
    currency = models.CharField(
        max_length=3,
        null=True,
        blank=True,
        help_text="Currency code",
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
        help_text="Timezone",
    )
    enforce_prescriptions = models.BooleanField(
        default=False,
        help_text="If enabled, prescription-required products require approved prescription",
    )
    enforce_controlled_substances = models.BooleanField(
        default=False,
        help_text="If enabled, controlled substances require approved prescription",
    )

    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Customization"
        verbose_name_plural = "Company Customizations"
        ordering = ["company"]

    def __str__(self):
        return f"{self.company.name} - Customization"
