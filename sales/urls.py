from django.urls import path
from rest_framework import routers
from .api import (
    SaleViewSet,
    SaleItemSet,
    SalePostSet,
    POSOrderViewSet,
    POSOrderItemViewSet,
    POSRefundViewSet,
    pos_sales_summary,
)


router = routers.DefaultRouter()

# Legacy endpoints
router.register("api/product/sales/list", SaleViewSet, "sale-get")
router.register("api/product/sales/post", SalePostSet, "sale-post")
router.register("api/product/sales/item", SaleItemSet, "sale-get")

# New POS endpoints
router.register("api/pos/orders", POSOrderViewSet, "pos-orders")
router.register("api/pos/order-items", POSOrderItemViewSet, "pos-order-items")
router.register("api/pos/refunds", POSRefundViewSet, "pos-refunds")

urlpatterns = [
    path("api/pos/sales-summary/", pos_sales_summary, name="pos_sales_summary"),
] + router.urls
