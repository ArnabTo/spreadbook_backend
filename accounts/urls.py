from rest_framework import routers
from accounts.api import AccountViewSet, BankAccountViewSet


router = routers.DefaultRouter()
router.register("api/accounts", AccountViewSet, "accounts")
router.register("api/user/fringe/list", BankAccountViewSet, "bank-get")

urlpatterns = router.urls
