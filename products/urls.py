from rest_framework import routers, urlpatterns
from django.urls import path
from .api import (
    ProductViewSet,
    ProductPostSet,
    PicturePostSet,
    NewLabelSet,
    SaleLabelSet,
    CategoryViewSet,
    UnitViewSet,
    PosProductIndexView,
    POSCatalogView,
    ProductOptionsView,
    ProductTypeViewSet,
    GenericNameViewSet,
    BrandViewSet,
    ProductBarcodeViewSet,
    ProductBatchViewSet,
    ProductSerialItemViewSet,
    StockTransferViewSet,
    UnitConversionGroupViewSet,
    UnitConversionStepViewSet,
)
from .api import ColorViewSet, SizeViewSet
from .inventory_api import (
    InventoryItemViewSet,
    InventoryCategoryViewSet,
    StockMovementViewSet,
    StockSummaryInventoryView,
    ProductStockView,
)


app_name = "api"

router = routers.DefaultRouter()
router.register("api/product/list", ProductViewSet, "product-get")
router.register("api/product/post", ProductPostSet, "product-post")
router.register("api/product/images", PicturePostSet, "product-images")
router.register("api/product/newlabel", NewLabelSet, "product-newLabel")
router.register("api/product/salelabel", SaleLabelSet, "product-saleLabel")

router.register("api/product/category", CategoryViewSet, "category")
router.register("api/product/units", UnitViewSet, "product-units")
router.register(
    "api/product/unit-conversion-groups",
    UnitConversionGroupViewSet,
    "unit-conversion-groups",
)
router.register(
    "api/product/unit-conversion-steps",
    UnitConversionStepViewSet,
    "unit-conversion-steps",
)
router.register("api/product/color", ColorViewSet, "color")
router.register("api/product/size", SizeViewSet, "size")

# MegaShop catalog helpers
router.register("api/product/types", ProductTypeViewSet, "product-types")
router.register("api/product/generic-names", GenericNameViewSet, "generic-names")
router.register("api/product/brands", BrandViewSet, "brands")
router.register("api/product/barcodes", ProductBarcodeViewSet, "product-barcodes")
router.register("api/product/batches", ProductBatchViewSet, "product-batches")

# Inventory Management APIs
router.register("api/inventory/items", InventoryItemViewSet, "inventory-items")
router.register(
    "api/inventory/categories", InventoryCategoryViewSet, "inventory-categories"
)
router.register("api/inventory/movements", StockMovementViewSet, "stock-movements")
router.register("api/product/serial-items", ProductSerialItemViewSet, "serial-items")
# Alternative path used by the stock-transfer frontend
router.register(
    "api/product-serial-items", ProductSerialItemViewSet, "serial-items-alt"
)
router.register("api/stock-transfers", StockTransferViewSet, "stock-transfers")


urlpatterns = router.urls

# POS / Dexie lightweight product index
urlpatterns = [
    path(
        "api/product/options/",
        ProductOptionsView.as_view(),
        name="product-options",
    ),
    path(
        "api/pos/product-index/",
        PosProductIndexView.as_view(),
        name="pos-product-index",
    ),
    path(
        "api/pos/catalog/",
        POSCatalogView.as_view(),
        name="pos-catalog",
    ),
    path(
        "api/inventory/stock-summary-items/",
        StockSummaryInventoryView.as_view(),
        name="inventory-stock-summary-items",
    ),
    path(
        "api/inventory/product-stock/<str:product_id>/",
        ProductStockView.as_view(),
        name="product-stock",
    ),
] + urlpatterns
