from rest_framework import routers

from .api import PrescriptionViewSet

router = routers.DefaultRouter()
router.register(
    "api/pharmacy/prescriptions", PrescriptionViewSet, "pharmacy-prescriptions"
)

urlpatterns = router.urls
