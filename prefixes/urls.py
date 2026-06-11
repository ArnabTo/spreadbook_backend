from rest_framework import routers
from .api import PrefixViewSet

router = routers.DefaultRouter()
router.register("api/prefixes", PrefixViewSet, "prefixes")

urlpatterns = router.urls
