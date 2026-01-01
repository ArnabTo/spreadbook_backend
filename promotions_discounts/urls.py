from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PromotionViewSet, PromotionUsageViewSet
from . import api

router = DefaultRouter()
router.register(r"promotions-viewset", PromotionViewSet, basename="promotion")
router.register(r"promotion-usage", PromotionUsageViewSet, basename="promotion-usage")

urlpatterns = [
    # Custom API endpoints (higher priority - specific paths first)
    path("api/promotions/all/", api.get_all_promotions, name="get_all_promotions"),
    path("api/promotions/create/", api.create_promotion, name="create_promotion"),
    path(
        "api/promotions/<uuid:promotion_id>/", api.get_promotion, name="get_promotion"
    ),
    path(
        "api/promotions/<uuid:promotion_id>/update/",
        api.update_promotion,
        name="update_promotion",
    ),
    path(
        "api/promotions/<uuid:promotion_id>/delete/",
        api.delete_promotion,
        name="delete_promotion",
    ),
    path(
        "api/promotions/<uuid:promotion_id>/toggle-status/",
        api.toggle_promotion_status,
        name="toggle_promotion_status",
    ),
    path(
        "api/promotions/validate-code/",
        api.validate_promotion_code,
        name="validate_promotion_code",
    ),
    path("api/promotions/stats/", api.get_promotion_stats, name="get_promotion_stats"),
    path("api/promotions/usage/", api.get_promotion_usage, name="get_promotion_usage"),
    path(
        "api/promotions/<uuid:promotion_id>/usage/",
        api.get_promotion_usage,
        name="get_promotion_usage_by_id",
    ),
    # DRF ViewSets (lower priority - generic patterns last)
    path("api/", include(router.urls)),
]

app_name = "promotions_discounts"
