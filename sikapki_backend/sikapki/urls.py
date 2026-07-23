"""
URL utama project. Setiap app punya urls.py sendiri, di-include di sini
dengan prefix /api/<nama-app>/ supaya rapi dan mudah ditambah.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from core.views import HealthCheckView
from .admin_dashboard import configure_admin_dashboard

configure_admin_dashboard()

urlpatterns = [
    # Endpoint pendek untuk health check container/load balancer.
    path('healthz', HealthCheckView.as_view(), name='healthz'),
    path('admin/', admin.site.urls),

    # Etiket pembanding adalah dokumen publik DJKI. Jalur ini sengaja dibatasi
    # ke folder etiket agar dokumen knowledge base tidak ikut terbuka.
    path(
        'media/trademark/referensi/<path:path>', serve,
        {'document_root': settings.MEDIA_ROOT / 'trademark' / 'referensi'},
        name='trademark-reference-media',
    ),

    path('api/core/', include('core.urls')),
    path('api/knowledge/', include('knowledge.urls')),
    path('api/trademark/', include('trademark.urls')),
    path('api/chatbot/', include('chatbot.urls')),
]

# Static asset untuk demo/local LAN saat DEBUG=False. Deployment publik
# sebaiknya mematikan opsi ini dan menggunakan web server khusus static files.
if settings.SERVE_STATIC_FILES:
    urlpatterns += [
        re_path(
            r'^static/(?P<path>.*)$', serve,
            {'document_root': settings.STATIC_ROOT},
            name='static-files',
        ),
    ]

# Serving media files saat development (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
