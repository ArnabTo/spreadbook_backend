from django.db import models
from functools import cached_property
# from Backend.ERP_Shop.payroll.models import PAYMENT_CHOICE
from common.utils import INDUSTRYCHOICES
from django.contrib.auth.models import AbstractUser
from django.contrib.sessions.models import Session
from django.core.validators import RegexValidator
from django.db import models
from django.utils.timezone import now

from django.utils.translation import gettext_lazy as _

from .manager import UserManager


def upload_to_beand_logo(instance, filename):
    from datetime import datetime

    return datetime.now().strftime("assets/uploads/brand/logo/%Y/%m/") + filename


def upload_to_avater(instance, filename):
    from datetime import datetime

    return datetime.now().strftime("assets/uploads/brand/avater/%Y/%m/") + filename


TYPE_CHOICE = (
    ("Home", "Home"),
    ("Office", "Office"),
    ("Wirehouse", "Wirehouse"),
    ("Other", "Other"),
)

ROLE_CHOICE = (
    ("software_owner", "Software Owner"),
    ("reseller", "Reseller"),
    ("super_admin", "Super Admin"),
    ("admin", "Admin"),
    ("manager", "Manager"),
    ("staff", "Staff"),
    ("waiter", "Waiter"),
    ("chef", "Chef"),
    ("cashier", "Cashier"),
    # Legacy roles for backward compatibility
    ("CFO", "CFO"),
    ("CTO", "CTO"),
    ("CEO", "CEO"),
    ("Managing Director", "Managing Director"),
    ("Chairman", "Chairman"),
    ("Salesman", "Salesman"),
    ("HR", "HR"),
    ("Accountant", "Accountant"),
    ("Quality Assurance Specialist", "Quality Assurance Specialist"),
    ("Customer Service Associate", "Customer Service Associate"),
    ("Sales Representative", "Sales Representative"),
    ("Operations Manager", "Operations Manager"),
    ("Marketing Director", "Marketing Director"),
    ("Customer", "Customer"),
    ("Employee", "Employee"),
    ("Supplier", "Supplier"),
    ("Auditor", "Auditor"),
    ("Founder", "Founder"),
)

STATUS_CHOICE = (
    ("active", "active"),
    ("banned", "banned"),
    ("pending", "pending"),
    ("rejected", "rejected"),
)


class User(AbstractUser):
    """Customize default User model"""

    email = models.EmailField(unique=True)
    name = models.CharField(
        verbose_name=_("Owner Name"),
        max_length=50,
    )
    
    # companyId = models.CharField(max_length=100, default="", blank=True, null=True)
    
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    # resellerId = models.CharField(max_length=100, default="", blank=True, null=True)
    resellerId = models.ForeignKey(
        "reseller.Reseller",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # branchAccess = models.JSONField(
    #     default=list,
    #     blank=True,
    #     help_text="Array of branch IDs user can access or ['all']",
    # )
    branchAccess = models.ManyToManyField(
        "company.Branch",
        blank=True,
        help_text="Branches this user can access",
    )
    payroll = models.OneToOneField(
        "payroll.SetEmployeePayroll",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    role = models.CharField(
        max_length=100, choices=ROLE_CHOICE, default="", blank=True, null=True
    )
    phone_regex = RegexValidator(
        regex=r"^(?:\+88|88)?(01[3-9]\d{8})$",
        message="Phone number must be entered in the format: '+8801XXXXXX'. Up to 14 digits allowed.",
    )
    phoneNumber = models.CharField(
        
        max_length=20,
        unique=True,
        null=True,
        blank=True,
    )
    fullAddress = models.CharField(max_length=200, default="", blank=True, null=True)
    addressType = models.CharField(
        max_length=100, choices=TYPE_CHOICE, default="", blank=True, null=True
    )
    primary = models.BooleanField(default=False, blank=True, null=True)
    city = models.CharField(max_length=100, default="", blank=True, null=True)
    country = models.CharField(max_length=100, default="", blank=True, null=True)
    state = models.CharField(max_length=100, default="", blank=True, null=True)
    status = models.CharField(
        max_length=100, choices=STATUS_CHOICE, default="", blank=True, null=True
    )
    zipCode = models.CharField(max_length=100, default="", blank=True, null=True)
    about = models.CharField(max_length=100, default="", blank=True, null=True)
    company = models.CharField(
        verbose_name=_("Organization Name"), max_length=50, null=True, blank=True
    )
    companyAddress = models.CharField(max_length=200, default="", blank=True, null=True)
    address = models.CharField(max_length=200, default="", blank=True, null=True)
    business = models.CharField(
        verbose_name=_("Business"),
        max_length=50,
        choices=INDUSTRYCHOICES,
        help_text=_("Select your business type:"),
        null=True,
        blank=True,
    )
    business_manager_name = models.CharField(
        verbose_name=_("Business Manager Name"), max_length=50, null=True, blank=True
    )
    # brand_logo = CloudinaryField('Brand Logo', null=True, blank=True)
    brand_logo = models.ImageField(
        upload_to=upload_to_beand_logo, blank=True, null=True
    )
    defaultURL = models.URLField(null=True, blank=True)
    avatarUrl = models.ImageField(upload_to=upload_to_avater, blank=True, null=True)

    otp = models.SmallIntegerField(help_text="One Time Password", null=True, blank=True)
    token = models.CharField(
        verbose_name=_("Token"),
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        help_text="Token for authentication",
    )
    ip_address = models.GenericIPAddressField(
        verbose_name=_("IP Address"), help_text="IP Address", blank=True, null=True
    )
    is_verified = models.BooleanField(
        _("verified"),
        default=False,
        help_text=_(
            "Designates whether this user has been verified."
            "Un-verified users cannot log in."
        ),
    )
    is_founder = models.BooleanField(
        _("founder"),
        default=False,
        help_text=_("Designates whether this user should be treated as founder."),
    )
    is_ceo = models.BooleanField(
        _("ceo"),
        default=False,
        help_text=_("Designates whether this user should be treated as CEO."),
    )
    is_admin = models.BooleanField(
        _("admin"),
        default=False,
        help_text=_("Designates whether this user should be treated as admin."),
    )
    is_manager = models.BooleanField(
        _("manager"),
        default=False,
        help_text=_("Designates whether this user should be treated as manager."),
    )
    is_head_office = models.BooleanField(
        _("head office"),
        default=False,
        help_text=_("Designates whether this user should be treated as head office."),
    )
    is_hr = models.BooleanField(
        _("hr"),
        default=False,
        help_text=_(
            "Designates whether this user should be treated as Human resources (HR)."
        ),
    )
    is_accountant = models.BooleanField(
        _("accountant"),
        default=False,
        help_text=_("Designates whether this user should be treated as accountant."),
    )
    is_auditor = models.BooleanField(
        _("auditor"),
        default=False,
        help_text=_("Designates whether this user should be treated as auditor."),
    )
    is_auditor_manager = models.BooleanField(
        _("auditor manager"),
        default=False,
        help_text=_(
            "Designates whether this user should be treated as auditor manager."
        ),
    )
    is_auditor_head_office = models.BooleanField(
        _("auditor head office"),
        default=False,
        help_text=_(
            "Designates whether this user should be treated as auditor head office."
        ),
    )
    is_employee = models.BooleanField(
        _("employee"),
        default=False,
        help_text=_("Designates whether this user should be treated as employee."),
    )
    is_customer = models.BooleanField(
        _("customer"),
        default=False,
        help_text=_("Designates whether this user should be treated as customer."),
    )
    is_supplier = models.BooleanField(
        _("supplier"),
        default=False,
        help_text=_("Designates whether this user should be treated as supplier."),
    )

    # Timestamps fields
    otp_created_time = models.DateTimeField(
        default=now,
        verbose_name=_("OTP created time"),
        editable=False,
    )
    password_changes_datatime = models.DateTimeField(
        verbose_name=_("Password changes datatime"),
        blank=True,
        null=True,
    )
    login_datetime = models.DateTimeField(
        verbose_name=_("Login datetime"),
        blank=True,
        null=True,
    )
    logout_datetime = models.DateTimeField(
        verbose_name=_("Logout datetime"),
        blank=True,
        null=True,
    )
    last_activity = models.DateTimeField(
        verbose_name=_("Last activity"),
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(default=now, editable=False)

    session = models.OneToOneField(
        Session, on_delete=models.CASCADE, blank=True, null=True
    )

    # Restaurant Management System specific fields
    # companyId = models.CharField(
    #     max_length=100,
    #     null=True,
    #     blank=True,
    #     help_text="Company ID for multi-tenant system",
    # )
    # resellerId = models.CharField(
    #     max_length=100,
    #     null=True,
    #     blank=True,
    #     help_text="Reseller ID for reseller users",
    # )
    # branchAccess = models.JSONField(
    #     default=list,
    #     blank=True,
    #     help_text="Array of branch IDs user can access or ['all']",
    # )
    fullName = models.CharField(
        max_length=100, blank=True, null=True, help_text="Full display name"
    )

    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["-created_at"]

    objects = UserManager()

    def __str__(self):
        return self.username or self.email

    def save(self, *args, **kwargs):
        # If no username is set, use email as username
        if not self.username:
            self.username = self.email
        # Set fullName from name if not provided
        if not self.fullName and self.name:
            self.fullName = self.name
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"





