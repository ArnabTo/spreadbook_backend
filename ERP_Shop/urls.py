from settings import urls as SystemSettings
from supplier_ledger import urls as SupplierLedger
from common import urls as Common
from pharmacy import urls as Pharmacy
from inventory_log import urls as InventoryLog
from purchase import urls as Purchase
from resort import urls as Resort
from hotel import urls as Hotel
from reports import urls as Reports
from dashboard import urls as Dashboard
from recipe_waste_management import urls as RecipeWasteManagement
from promotions_discounts import urls as PromotionsDiscounts
from booking import urls as Booking
from table_managment import urls as TableManagement
from menu_items import urls as MenuItems
from suppliers import urls as Suppliers
from payroll import urls as Payroll
from reseller import urls as Reseller
from portfolio import urls as Portfolio
from calendar_events import urls as CalendarEvents
from expense import urls as Expense
from my_project import urls as Project
from blog import urls as BlogPost
from account_groups import urls as AccountGroups
from accounts import urls as LedgerAccounts
from financial_years import urls as FinancialYears
from prefixes import urls as Prefixes
from authenticator import urls as GenUser
from company import urls as Company
from customers import urls as Customer
from service import urls as Service
from sales import urls as Sales
from sales_quotation import urls as SalesQuotation
from review import urls as PeopleReview
from products import urls as Product
from order import urls as Orders
from django.contrib import admin
from django.urls import path, include
from django_otp.admin import OTPAdminSite
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Raktch Portal"
admin.site.site_title = "Raktch ERP Platform"
admin.site.index_title = "Raktch ERP Platform"
admin.autodiscover()


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),  # JWT based
    path("auth/", include("djoser.urls.authtoken")),  # AuthToken based
    path("", include(BlogPost)),
    path("", include(Booking)),
    path("", include(CalendarEvents)),
    path("", include(Common)),
    path("", include(Company)),
    path("", include(Customer)),
    path("", include(Expense)),
    path("", include(GenUser)),
    path("", include(Hotel)),
    path("", include(Resort)),
    path("", include(MenuItems)),
    path("", include(Orders)),
    path("", include(PeopleReview)),
    path("", include(Portfolio)),
    path("", include(Product)),
    path("", include(Project)),
    path("", include(PromotionsDiscounts)),
    path("", include(RecipeWasteManagement)),
    path("", include(AccountGroups)),
    path("", include(LedgerAccounts)),
    path("", include(FinancialYears)),
    path("", include(Prefixes)),
    path("api/dashboard/", include(Dashboard)),
    path("api/reports/", include(Reports)),
    path("api/", include(Reseller)),
    path("", include(Payroll)),
    path("", include(InventoryLog)),
    path("", include(Purchase)),
    path("", include(Pharmacy)),
    path("", include(Sales)),
    path("", include(SalesQuotation)),
    path("", include(Service)),
    path("", include(Suppliers)),
    path("", include(TableManagement)),
    path("", include(SupplierLedger)),
    path("", include(SystemSettings)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
