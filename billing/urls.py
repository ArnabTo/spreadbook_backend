from rest_framework import routers, urlpatterns
from .api import BillingViewSet


router = routers.DefaultRouter()
router.register('api/company/acoount/billing', BillingViewSet, 'billing-get')

urlpatterns = router.urls