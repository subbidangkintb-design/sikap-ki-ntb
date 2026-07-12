from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import CekMerekAIViewSet, CekMerekLogViewSet, MirrorPDKIViewSet

router = DefaultRouter()
router.register('mirror-pdki', MirrorPDKIViewSet, basename='mirrorpdki')
router.register('cek-merek-log', CekMerekLogViewSet, basename='cekmereklog')

cek_merek_ai = CekMerekAIViewSet.as_view({'post': 'cek'})

urlpatterns = [
    path('cek/', cek_merek_ai, name='trademark-cek-ai'),
]

urlpatterns += router.urls
