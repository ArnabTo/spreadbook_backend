from rest_framework import routers
from .api import FinancialYearViewSet

router = routers.DefaultRouter()
router.register("api/financial-years", FinancialYearViewSet, "financial-years")

urlpatterns = router.urls
