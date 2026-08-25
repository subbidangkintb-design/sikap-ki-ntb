from django.urls import path
from .views import BackgroundJobStatusView, HealthCheckView, MeView, StatistikLayananView, UjiCobaPenggunaView

urlpatterns = [
    path('me/', MeView.as_view(), name='core-me'),
    path('jobs/<uuid:job_id>/', BackgroundJobStatusView.as_view(), name='background-job-status'),
    path('statistik-layanan/', StatistikLayananView.as_view(), name='statistik-layanan'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('uji-coba/', UjiCobaPenggunaView.as_view(), name='uji-coba-pengguna'),
]
