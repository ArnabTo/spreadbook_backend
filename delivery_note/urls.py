from rest_framework.routers import DefaultRouter

from .api import DeliveryNoteViewSet

router = DefaultRouter()
router.register(
    "api/delivery-notes", DeliveryNoteViewSet, "delivery-notes"
)

urlpatterns = router.urls
