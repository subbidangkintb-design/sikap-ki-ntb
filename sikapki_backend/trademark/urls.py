from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    CekMerekAIViewSet,
    CekMerekLogViewSet,
    KlasifikasiMerekLogViewSet,
    MirrorPDKIViewSet,
)

router = DefaultRouter()
router.register('mirror-pdki', MirrorPDKIViewSet, basename='mirrorpdki')
router.register('cek-merek-log', CekMerekLogViewSet, basename='cekmereklog')
router.register(
    'klasifikasi-merek-log',
    KlasifikasiMerekLogViewSet,
    basename='klasifikasimereklog',
)

cek_merek_ai = CekMerekAIViewSet.as_view({'post': 'cek'})
cek_kemiripan_ai = CekMerekAIViewSet.as_view({'post': 'cek_kemiripan'})
fitur_merek = CekMerekAIViewSet.as_view({'get': 'fitur'})
eskalasi_kelas = CekMerekAIViewSet.as_view({'post': 'eskalasi_kelas'})

urlpatterns = [
    path('cek/', cek_merek_ai, name='trademark-cek-ai'),
    path('cek-kemiripan/', cek_kemiripan_ai, name='trademark-cek-kemiripan-ai'),
    path('fitur/', fitur_merek, name='trademark-fitur'),
    path('cek-kelas/eskalasi/', eskalasi_kelas, name='trademark-cek-kelas-eskalasi'),
]

urlpatterns += router.urls
