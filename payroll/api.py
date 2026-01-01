from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import (
    # EmployeePayroll,
    SetEmployeePayroll,
    AdditionPayroll,
    OverTimePayroll,
    DeductionPayroll,
    EmployeePaySlip,
)
from .serializers import (
    # EmployeePayrollSerializer,
    SetEmployeePayrollSerializer,
    SetEmployeePayrollListSerializer,
    AdditionPayrollSerializer,
    OverTimePayrollSerializer,
    DeductionPayrollSerializer,
    EmployeePaySlipSerializer,
    # UserEmployeeListSerializer
    EmployeePaySlipListSerializer,
)

from authenticator.models import User as GenUser
from rest_framework import serializers, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


class SetEmployeePayrollViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = SetEmployeePayrollSerializer

    def get_queryset(self):
        return SetEmployeePayroll.objects.filter(
            company_id=self.request.user.company_id
        )

    @action(detail=False, methods=["get"])
    def by_employee(self, request):
        """Get payroll settings by employee ID"""
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            return Response(
                {"error": "employee_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payroll_setting = SetEmployeePayroll.objects.get(
                employee_id=employee_id, company_id=self.request.user.company_id
            )
            serializer = self.get_serializer(payroll_setting)
            return Response(serializer.data)
        except SetEmployeePayroll.DoesNotExist:
            return Response(
                {"error": "Payroll setting not found for this employee"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"])
    def set_bulk_payroll(self, request):
        """Set payroll for multiple employees at once"""
        employees_data = request.data.get("employees", [])
        if not employees_data:
            return Response(
                {"error": "employees data is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_payrolls = []
        errors = []

        for employee_data in employees_data:
            serializer = self.get_serializer(data=employee_data)
            if serializer.is_valid():
                # Check if payroll already exists for this employee
                existing_payroll = SetEmployeePayroll.objects.filter(
                    employee_id=employee_data.get("employee"),
                    company_id=self.request.user.company_id,
                ).first()

                if existing_payroll:
                    # Update existing payroll
                    for attr, value in serializer.validated_data.items():
                        setattr(existing_payroll, attr, value)
                    existing_payroll.save()
                    created_payrolls.append(
                        SetEmployeePayrollSerializer(existing_payroll).data
                    )
                else:
                    # Create new payroll
                    payroll = serializer.save()
                    created_payrolls.append(serializer.data)
            else:
                errors.append(
                    {"employee_data": employee_data, "errors": serializer.errors}
                )

        return Response(
            {"created_payrolls": created_payrolls, "errors": errors},
            status=(
                status.HTTP_201_CREATED
                if created_payrolls
                else status.HTTP_400_BAD_REQUEST
            ),
        )


class SetEmployeePayrollListViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = SetEmployeePayrollListSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        queryset = SetEmployeePayroll.objects.filter(
            company_id=self.request.user.company_id
        )

        # Filter by employee if specified
        employee_id = self.request.query_params.get("employee_id")
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)

        # Filter by payment type if specified
        payment_type = self.request.query_params.get("payment_type")
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)

        # Filter by status if specified
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related("employee", "creator").order_by("-id")


# class EmployeePayrollViewSet(viewsets.ModelViewSet):
#      authentication_classes = [TokenAuthentication]
#      permission_classes = [IsAuthenticated]

#      # queryset = Product.objects.all()
#      serializer_class = EmployeePayrollSerializer
#      # http_method_names= ['get']
#      def get_queryset(self):
#           return EmployeePayroll.objects.filter(company_id=self.request.user.company_id)

# class UserEmployeeListViewSet(viewsets.ModelViewSet):
#      authentication_classes = [TokenAuthentication]
#      permission_classes = [IsAuthenticated]

#      # queryset = Product.objects.all()
#      serializer_class = UserEmployeeListSerializer
#      # http_method_names= ['get']
#      def get_queryset(self):
#           return GenUser.objects.filter(company_id=self.request.user.company_id)


class AdditionPayrollViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # queryset = Product.objects.all()
    serializer_class = AdditionPayrollSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return AdditionPayroll.objects.filter(company_id=self.request.user.company_id)


class OverTimePayrollViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # queryset = Product.objects.all()
    serializer_class = OverTimePayrollSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return OverTimePayroll.objects.filter(company_id=self.request.user.company_id)


class DeductionPayrollViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # queryset = Product.objects.all()
    serializer_class = DeductionPayrollSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return DeductionPayroll.objects.filter(company_id=self.request.user.company_id)


class EmployeePaySlipViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # queryset = Product.objects.all()
    serializer_class = EmployeePaySlipSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return EmployeePaySlip.objects.filter(company_id=self.request.user.company_id)


class EmployeePaySlipListViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # queryset = Product.objects.all()
    serializer_class = EmployeePaySlipListSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        return EmployeePaySlip.objects.filter(
            company_id=self.request.user.company_id
        ).order_by("-createDate")
