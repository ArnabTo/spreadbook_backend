from django.urls import path
from rest_framework import routers
from .api import (
    CountryViewSet,
    StateProvinceViewSet,
    CompanyViewSet,
    BranchViewSet,
    CompanyCustomizationViewSet,
    WarehouseViewSet,
)
from .api_enhanced import (
    get_companies_with_branches,
    get_user_accessible_branches,
    assign_user_to_branches,
    get_branch_users,
    get_company_structure,
    create_user_with_branch_access,
    company_signup,
)


router = routers.DefaultRouter()
router.register("api/companies", CompanyViewSet, "companies")
router.register("api/branches", BranchViewSet, "branches")
router.register("api/warehouses", WarehouseViewSet, "warehouses")
router.register("api/countries", CountryViewSet, "countries")
router.register("api/states", StateProvinceViewSet, "states")
router.register(
    "api/company-customizations", CompanyCustomizationViewSet, "company-customizations"
)

# Keep legacy endpoint for backward compatibility
router.register("api/company/list", CompanyViewSet, "company-get")

# Enhanced API endpoints for user-company-branch relationships
enhanced_urlpatterns = [
    path(
        "api/company/signup/",
        company_signup,
        name="company-signup",
    ),
    path(
        "api/companies-with-branches/",
        get_companies_with_branches,
        name="companies-with-branches",
    ),
    path(
        "api/user/accessible-branches/",
        get_user_accessible_branches,
        name="user-accessible-branches",
    ),
    path(
        "api/users/assign-branches/",
        assign_user_to_branches,
        name="assign-user-branches",
    ),
    path("api/branches/<int:branch_id>/users/",
         get_branch_users, name="branch-users"),
    path(
        "api/companies/<int:company_id>/structure/",
        get_company_structure,
        name="company-structure",
    ),
    path(
        "api/users/create-with-branches/",
        create_user_with_branch_access,
        name="create-user-with-branches",
    ),
]

urlpatterns = router.urls + enhanced_urlpatterns
