from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from utils.models.common_fields import Timestamp
import uuid
from django.utils.timezone import now

from django.contrib.auth import get_user_model

User = get_user_model()

TYPE_CHOICE = (
    ("Remuneration", "Remuneration"),
    ("Additional Remuneration", "Additional Remuneration"),
    ("Other", "Other"),
)

STATUS_CHOICE = (
    ("paid", "paid"),
    ("advance", "advance"),
)

PAYMENT_CHOICE = (
    ("cash", "cash"),
    ("bank", "bank"),
)


class SetEmployeePayroll(models.Model):
    #     creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owner_payroll_model', blank=True, null=True)
    company_id = models.CharField(max_length=100, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)
    #     employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owner_payroll_employee', blank=True, null=True)
    salary = models.FloatField(default=0)
    payment_type = models.CharField(
        max_length=100, choices=PAYMENT_CHOICE, default="cash", blank=True, null=True
    )
    status = models.CharField(
        max_length=100, choices=STATUS_CHOICE, default="active", blank=True, null=True
    )


class BasePayroll(models.Model):
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owner_base_payroll_model",
        blank=True,
        null=True,
    )
    company_id = models.CharField(max_length=100, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)

    name = models.CharField(max_length=100, null=True, blank=True)
    amount = models.FloatField(default=0)

    assignee = models.ManyToManyField(User, related_name="base_assignee", blank=True)


class AdditionPayroll(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owner_addition_model",
        blank=True,
        null=True,
    )
    company_id = models.CharField(max_length=100, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)

    category = models.CharField(
        max_length=100,
        choices=TYPE_CHOICE,
        default="Remuneration",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=100, null=True, blank=True)
    amount = models.FloatField(default=0)

    assignee = models.ManyToManyField(User, related_name="assignee", blank=True)


class OverTimePayroll(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owner_overtime",
        blank=True,
        null=True,
    )
    company_id = models.CharField(max_length=100, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)

    name = models.CharField(max_length=100, null=True, blank=True)
    amount = models.FloatField(default=0)
    rate = models.CharField(max_length=100, null=True, blank=True)
    assignee = models.ManyToManyField(
        User, related_name="overtime_assignee", blank=True
    )


class DeductionPayroll(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owner_deduction",
        blank=True,
        null=True,
    )
    company_id = models.CharField(max_length=100, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)

    name = models.CharField(max_length=100, null=True, blank=True)
    amount = models.FloatField(default=0)
    rate = models.CharField(max_length=100, null=True, blank=True)
    assignee = models.ManyToManyField(
        User, related_name="deduction_assignee", blank=True
    )


class EmployeePaySlip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owner_employee_payslip_model",
        blank=True,
        null=True,
    )
    company_id = models.CharField(max_length=100, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)
    paySlipNumber = models.CharField(max_length=100, null=True, blank=True)

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owner_payslip_employee",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=100, choices=STATUS_CHOICE, default="paid", blank=True, null=True
    )

    description = models.TextField(null=True, blank=True)

    # payment source
    payment_method = models.CharField(
        max_length=100, choices=PAYMENT_CHOICE, default="cash", blank=True, null=True
    )
    last_amount = models.FloatField(default=0, blank=True, null=True)

    basic_salary = models.FloatField(default=0)
    # Payroll for month
    net_total = models.FloatField(default=0)
    # earning
    ta = models.FloatField(default=0)
    da = models.FloatField(default=0)
    ma = models.FloatField(default=0)
    hra = models.FloatField(default=0)
    bonus = models.FloatField(default=0)
    e_other = models.FloatField(default=0)
    total_earning = models.FloatField(default=0, blank=True, null=True)

    # Deduction
    tds = models.FloatField(default=0)
    esi = models.FloatField(default=0)
    pf = models.FloatField(default=0)
    leave = models.FloatField(default=0)
    d_other = models.FloatField(default=0)
    total_deduction = models.FloatField(default=0, blank=True, null=True)

    payroll_month = models.DateTimeField(blank=True, null=True)

    updateAt = models.DateTimeField(auto_now=True)
    createDate = models.DateTimeField(default=now, blank=True, null=True)
