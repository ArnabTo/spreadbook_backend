from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import MenuItemViewSet, MenuCategoryViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r"items", MenuItemViewSet, basename="menu-items")
router.register(r"categories", MenuCategoryViewSet, basename="menu-categories")

# The API URLs are now determined automatically by the router
urlpatterns = [
    path("api/menu/", include(router.urls)),
]

# Custom URL patterns for specific endpoints
app_name = "menu_items"
