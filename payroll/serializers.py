from decimal import Clamped

# from djoser.serializers import UserCreateSerializer  # Unused import
from django.contrib.auth import get_user_model

# from sales.models import SalesCash  # Commented out - model doesn't exist
from rest_framework import serializers
from company.models import Company
from .models import (
    # EmployeePayroll,
    SetEmployeePayroll,
    AdditionPayroll,
    OverTimePayroll,
    DeductionPayroll,
    EmployeePaySlip,
)

from authenticator.models import User as Genuser

User = get_user_model()


class SetEmployeePayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)
    employee_email = serializers.CharField(source="employee.email", read_only=True)
    employee_role = serializers.CharField(source="employee.role", read_only=True)
    creator_name = serializers.CharField(source="creator.name", read_only=True)

    class Meta:
        model = SetEmployeePayroll
        fields = [
            "id",
            "creator",
            "creator_name",
            "company_id",
            "company",
            "employee",
            "employee_name",
            "employee_email",
            "employee_role",
            "salary",
            "payment_type",
            "status",
        ]
        read_only_fields = ("creator", "company_id", "company", "creator_name")

    def create(self, validated_data):
        setEmployeePayroll = SetEmployeePayroll.objects.create(
            company_id=self.context["request"].user.company_id,
            creator=self.context["request"].user,
            company=self.context["request"].user.company,
            **validated_data,
        )
        return setEmployeePayroll

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class SetEmployeePayrollListSerializer(serializers.ModelSerializer):
    employee_details = serializers.SerializerMethodField()
    creator_details = serializers.SerializerMethodField()

    class Meta:
        model = SetEmployeePayroll
        fields = [
            "id",
            "creator",
            "creator_details",
            "company_id",
            "company",
            "employee",
            "employee_details",
            "salary",
            "payment_type",
            "status",
        ]

    def get_employee_details(self, obj):
        if obj.employee:
            return {
                "id": obj.employee.id,
                "name": obj.employee.name,
                "email": obj.employee.email,
                "role": obj.employee.role,
                "phone": getattr(obj.employee, "phoneNumber", None),
            }
        return None

    def get_creator_details(self, obj):
        if obj.creator:
            return {
                "id": obj.creator.id,
                "name": obj.creator.name,
                "email": obj.creator.email,
                "role": obj.creator.role,
            }
        return None


class AdditionPayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionPayroll
        fields = "__all__"

    def create(self, validated_data):
        additionPayroll = AdditionPayroll.objects.create(
            company_id=self.context["request"].user.company_id,
            creator=self.context["request"].user,
            company=self.context["request"].user.company,
            **validated_data,
        )
        return additionPayroll

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class OverTimePayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverTimePayroll
        fields = "__all__"

    def create(self, validated_data):
        overTimePayroll = OverTimePayroll.objects.create(
            company_id=self.context["request"].user.company_id,
            creator=self.context["request"].user,
            company=self.context["request"].user.company,
            **validated_data,
        )
        return overTimePayroll

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class DeductionPayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeductionPayroll
        fields = "__all__"

    def create(self, validated_data):
        deductionPayroll = DeductionPayroll.objects.create(
            company_id=self.context["request"].user.company_id,
            creator=self.context["request"].user,
            company=self.context["request"].user.company,
            **validated_data,
        )
        return deductionPayroll

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class EmployeePaySlipSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeePaySlip
        fields = "__all__"

    def create(self, validated_data):
        last_pay_slip = (
            EmployeePaySlip.objects.filter(
                company_id=self.context["request"].user.company_id
            )
            .order_by("createDate")
            .last()
        )
        if last_pay_slip is None:
            # company = Company.objects.get(company_id=self.context['request'].user.company_id)
            last_pay_slip = "PAYSLIP-1001"
        else:
            last_pay_slip = last_pay_slip.paySlipNumber

        paySlipNumber = last_pay_slip
        paySlip_int = int(paySlipNumber.split("PAYSLIP-")[-1])
        width = 4
        new_paySlip_int = paySlip_int + 1
        formatted = (width - len(str(new_paySlip_int))) * "0" + str(new_paySlip_int)
        new_paySlipNumber = "PAYSLIP-" + str(formatted)
        print(new_paySlipNumber)

        employeePaySlip = EmployeePaySlip.objects.create(
            company_id=self.context["request"].user.company_id,
            creator=self.context["request"].user,
            company=self.context["request"].user.company,
            paySlipNumber=new_paySlipNumber,
            **validated_data,
        )
        if employeePaySlip.payment_method == "cash":
            # TODO: Implement SalesCash model integration when available
            # salesCash = SalesCash.objects.filter(
            #     company_id=self.context["request"].user.company_id
            # )[0]

            # employeePaySlip.last_amount = salesCash.amount
            # employeePaySlip.save()

            # salesCash.amount = salesCash.amount - employeePaySlip.net_total
            # salesCash.save()

            # Update employee payroll status
            try:
                payUser = Genuser.objects.get(id=employeePaySlip.employee.id)
                if hasattr(payUser, "payroll") and payUser.payroll:
                    updatePayStatus = payUser.payroll
                    updatePayStatus.last_pay_month = employeePaySlip.payroll_month
                    updatePayStatus.save()
                    print(
                        f"Updated payroll for employee {employeePaySlip.employee.name} - {employeePaySlip.payroll_month}"
                    )
            except (Genuser.DoesNotExist, AttributeError) as e:
                print(f"Error updating payroll status: {e}")
            # print("Transfer " + str(employeePaySlip.net_total) + " Taka to " + employeePaySlip.paySlipNumber)

        return employeePaySlip

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class EmployeeDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "phoneNumber", "company", "role", "payroll"]
        depth = 1


class CreatorDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "phoneNumber", "company", "role", "payroll"]


class EmployeePaySlipListSerializer(serializers.ModelSerializer):
    employee = EmployeeDetailsSerializer(required=False)
    creator = CreatorDetailsSerializer(required=False)

    class Meta:
        model = EmployeePaySlip
        fields = "__all__"
        # depth = 2
