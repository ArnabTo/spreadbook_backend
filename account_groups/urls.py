from rest_framework import routers
from .api import AccountGroupViewSet, AccountGroupParentViewSet

router = routers.DefaultRouter()
router.register("api/account-groups", AccountGroupViewSet, "account-groups")
router.register("api/account-group-parents", AccountGroupParentViewSet, "account-group-parents")

urlpatterns = router.urls
