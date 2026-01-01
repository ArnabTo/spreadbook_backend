from rest_framework import routers
from django.urls import path, include
from .api import (
    UserViewSet,
    ResetPassUserViewSet,
    UpdateUserViewSet,
    CreateUserViewSet,
    RestaurantUserViewSet,
    restaurant_login,
    get_user_profile,
    UserCompanyViewSet,
    UserCompanyBranchViewSet,
    CreateCompanyUserViewSet,
)


router = routers.DefaultRouter()
# Legacy endpoints for backward compatibility
router.register("api/gen/user/list", UserViewSet, "user-get")
router.register("api/gen/user/company", UserCompanyViewSet, "user-company")
router.register("api/gen/user/create", CreateUserViewSet, "user-get")
router.register("api/gen/user/update", UpdateUserViewSet, "user-get")
router.register("api/gen/user/re-set/pass", ResetPassUserViewSet, "user-reset")

# New restaurant management endpoints
router.register("api/users", RestaurantUserViewSet, "restaurant-users")
router.register(
    "api/company-branch-users", UserCompanyBranchViewSet, "user-company-branch"
)
router.register(
    "api/create-company-users", CreateCompanyUserViewSet, "create-company-users"
)


# Custom paths for restaurant management system
urlpatterns = [
    path("api/auth/restaurant-login/", restaurant_login, name="restaurant-login"),
    path("api/auth/profile/", get_user_profile, name="user-profile"),
] + router.urls


# Enhanced Company-Branch User Endpoints with Permissions & Shifts
# GET /api/company-branch-users/	List users with company + branch filtering (includes permissions & shifts)
# GET /api/company-branch-users/by_branch/?branch_id=X	Filter by specific branch
# GET /api/company-branch-users/branch_managers/	Get managers with branch access
# GET /api/company-branch-users/by_role/?role=waiter	Filter by user role
# GET /api/company-branch-users/staff_with_permissions/?permission=pos	Filter by permission type
# POST /api/company-branch-users/{id}/update_permissions/	Update user permissions
# POST /api/company-branch-users/{id}/update_salary/	Update salary and payment type
# GET /api/company-branch-users/test_connection/	Test endpoint (verify API works)
