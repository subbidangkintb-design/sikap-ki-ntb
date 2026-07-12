"""
URL utama project. Setiap app punya urls.py sendiri, di-include di sini
dengan prefix /api/<nama-app>/ supaya rapi dan mudah ditambah.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .admin_dashboard import configure_admin_dashboard

configure_admin_dashboard()

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/core/', include('core.urls')),
    path('api/knowledge/', include('knowledge.urls')),
    path('api/trademark/', include('trademark.urls')),
    path('api/chatbot/', include('chatbot.urls')),
]

# Serving media files saat development (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
