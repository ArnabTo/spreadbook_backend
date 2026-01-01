from rest_framework import routers, urlpatterns
from django.urls import path
from .api import (
    ProductViewSet,
    ProductPostSet,
    PicturePostSet,
    NewLabelSet,
    SaleLabelSet,
    CategoryViewSet,
    PosProductIndexView,
)
from .api import ColorViewSet, SizeViewSet
from .inventory_api import (
    InventoryItemViewSet,
    InventoryCategoryViewSet,
    StockMovementViewSet,
)


app_name = "api"

router = routers.DefaultRouter()
router.register("api/product/list", ProductViewSet, "product-get")
router.register("api/product/post", ProductPostSet, "product-post")
router.register("api/product/images", PicturePostSet, "product-images")
router.register("api/product/newlabel", NewLabelSet, "product-newLabel")
router.register("api/product/salelabel", SaleLabelSet, "product-saleLabel")

router.register("api/product/category", CategoryViewSet, "category")
router.register("api/product/color", ColorViewSet, "color")
router.register("api/product/size", SizeViewSet, "size")

# Inventory Management APIs
router.register("api/inventory/items", InventoryItemViewSet, "inventory-items")
router.register(
    "api/inventory/categories", InventoryCategoryViewSet, "inventory-categories"
)
router.register("api/inventory/movements", StockMovementViewSet, "stock-movements")


urlpatterns = router.urls

# POS / Dexie lightweight product index
urlpatterns = [
    path(
        "api/pos/product-index/",
        PosProductIndexView.as_view(),
        name="pos-product-index",
    ),
] + urlpatterns
