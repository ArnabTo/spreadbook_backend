from rest_framework import routers
from .api import (
    ExpenseViewSet,
    CategoryViewSet,
    ExpensetViewSet,
    ExpensePostViewSet,  # Legacy viewsets
)

router = routers.DefaultRouter()

# Modern API endpoints
router.register("api/expenses", ExpenseViewSet, "expenses")
router.register("api/categories", CategoryViewSet, "categories")

# Legacy API endpoints for backward compatibility
router.register("api/expense", ExpensetViewSet, "expense-get")
router.register("api/expense-post", ExpensePostViewSet, "expense-post")

urlpatterns = router.urls
