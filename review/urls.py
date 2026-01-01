from rest_framework import routers, urlpatterns
from .api import PeopleReviewViewSet


router = routers.DefaultRouter()
router.register('api/post/people', PeopleReviewViewSet, 'post-get')
# router.register('api/post/blog/', PostViewSet, 'slug')


urlpatterns = router.urls