from django.db.models import F, Q
from rest_framework import viewsets, permissions
from .models import KategoriKI, DokumenResmi, FAQ
from .serializers import KategoriKISerializer, DokumenResmiSerializer, FAQSerializer


class KategoriKIViewSet(viewsets.ModelViewSet):
    queryset = KategoriKI.objects.all()
    serializer_class = KategoriKISerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class DokumenResmiViewSet(viewsets.ModelViewSet):
    queryset = DokumenResmi.objects.all()
    serializer_class = DokumenResmiSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(diupload_oleh=user)


class FAQViewSet(viewsets.ModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset().select_related('kategori')
        q = self.request.query_params.get('q', '').strip()
        kategori = self.request.query_params.get('kategori', '').strip()

        if q:
            queryset = queryset.filter(
                Q(pertanyaan__icontains=q)
                | Q(jawaban__icontains=q)
                | Q(kategori__nama__icontains=q)
            )
        if kategori:
            queryset = queryset.filter(kategori_id=kategori)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        # Setiap kali FAQ dibuka, naikkan jumlah_dilihat secara atomik
        # (pakai F() supaya aman dari race condition saat diakses bersamaan).
        FAQ.objects.filter(pk=kwargs['pk']).update(jumlah_dilihat=F('jumlah_dilihat') + 1)
        return super().retrieve(request, *args, **kwargs)
