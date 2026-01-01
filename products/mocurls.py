from rest_framework import routers, urlpatterns
from .api import RatingViewSet, ReviewViewSet
from .api import ListProductViewSet, PostProductViewSet, PicturePostSet, NewLabelSet, SaleLabelSet,UpdateProductViewSet


app_name = 'api'

router = routers.DefaultRouter()
router.register('api/product/list', ListProductViewSet, 'product-get')
router.register('api/product/post', PostProductViewSet, 'product-post')
router.register('api/product/update', UpdateProductViewSet, 'product-post')
router.register('api/product/images', PicturePostSet, 'product-images')
router.register('api/product/newlabel', NewLabelSet, 'product-newLabel')
router.register('api/product/salelabel', SaleLabelSet, 'product-saleLabel')

router.register('api/product/review', ReviewViewSet, 'review-newLabel')
router.register('api/product/rating', RatingViewSet, 'rating-saleLabel')


urlpatterns = router.urls