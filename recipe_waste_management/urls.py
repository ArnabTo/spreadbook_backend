from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecipeViewSet, WasteRecordViewSet

router = DefaultRouter()
router.register(r"recipes", RecipeViewSet, basename="recipe")
router.register(r"waste-records", WasteRecordViewSet, basename="waste-record")

urlpatterns = [
    # DRF ViewSets
    path("api/", include(router.urls)),
]

app_name = "recipe_waste_management"
