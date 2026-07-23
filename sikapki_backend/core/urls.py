from django.urls import path
from .views import HealthCheckView, MeView, StatistikLayananView, UjiCobaPenggunaView

urlpatterns = [
    path('me/', MeView.as_view(), name='core-me'),
    path('statistik-layanan/', StatistikLayananView.as_view(), name='statistik-layanan'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('uji-coba/', UjiCobaPenggunaView.as_view(), name='uji-coba-pengguna'),
]
