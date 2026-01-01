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

from order import urls as Orders
from products import urls as Product
from review import urls as PeopleReview
from sales import urls as Sales
from service import urls as Service
from customers import urls as Customer
from company import urls as Company
from authenticator import urls as GenUser
from blog import urls as BlogPost
from my_project import urls as Project
from expense import urls as Expense
from calendar_events import urls as CalendarEvents
from portfolio import urls as Portfolio
from reseller import urls as Reseller
from payroll import urls as Payroll
from suppliers import urls as Suppliers
from menu_items import urls as MenuItems
from table_managment import urls as TableManagement
from booking import urls as Booking
from promotions_discounts import urls as PromotionsDiscounts
from recipe_waste_management import urls as RecipeWasteManagement
from dashboard import urls as Dashboard
from reports import urls as Reports
from hotel import urls as Hotel
from resort import urls as Resort
from purchase import urls as Purchase
from pharmacy import urls as Pharmacy
from common import urls as Common

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
    path("api/dashboard/", include(Dashboard)),
    path("api/reports/", include(Reports)),
    path("api/", include(Reseller)),
    path("", include(Payroll)),
    path("", include(Purchase)),
    path("", include(Pharmacy)),
    path("", include(Sales)),
    path("", include(Service)),
    path("", include(Suppliers)),
    path("", include(TableManagement)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
