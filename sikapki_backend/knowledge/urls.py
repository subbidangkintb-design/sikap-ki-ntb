from rest_framework.routers import DefaultRouter
from .views import KategoriKIViewSet, DokumenResmiViewSet, FAQViewSet

router = DefaultRouter()
router.register('kategori', KategoriKIViewSet, basename='kategoriki')
router.register('dokumen', DokumenResmiViewSet, basename='dokumenresmi')
router.register('faq', FAQViewSet, basename='faq')

urlpatterns = router.urls
