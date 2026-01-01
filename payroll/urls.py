from rest_framework import routers, urlpatterns
from .api import (
    # EmployeePayrollViewSet,
    SetEmployeePayrollViewSet,
    SetEmployeePayrollListViewSet,
    AdditionPayrollViewSet,
    OverTimePayrollViewSet,
    DeductionPayrollViewSet,
    EmployeePaySlipViewSet,
    # UserEmployeeListViewSet
    EmployeePaySlipListViewSet,
)

router = routers.DefaultRouter()
# router.register('api/employee/list', UserEmployeeListViewSet, 'employee-get')
# router.register('api/employee/payroll/list', EmployeePayrollViewSet, 'employee-get')
router.register(
    "api/employee/payroll/settings", SetEmployeePayrollViewSet, "payroll-settings"
)
router.register(
    "api/employee/payroll/settings-list",
    SetEmployeePayrollListViewSet,
    "payroll-settings-list",
)
router.register("api/employee/payroll/addition", AdditionPayrollViewSet, "addition-get")
router.register("api/employee/payroll/overtime", OverTimePayrollViewSet, "overtime-get")
router.register(
    "api/employee/payroll/deduction", DeductionPayrollViewSet, "deduction-get"
)
router.register("api/employee/payslip", EmployeePaySlipViewSet, "payslip-post")
router.register("api/employee/pays", EmployeePaySlipListViewSet, "payslip-list")

urlpatterns = router.urls
