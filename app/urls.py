from .views import ProjectViewSet, StackViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"projects/(?P<project>[^/.]+)", StackViewSet, basename="stack")
urlpatterns = router.urls
