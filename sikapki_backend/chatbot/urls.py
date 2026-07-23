from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import ChatbotViewSet, PercakapanChatbotViewSet, StatusKonsultasiView

router = DefaultRouter()
router.register('percakapan', PercakapanChatbotViewSet, basename='percakapanchatbot')

chatbot_tanya = ChatbotViewSet.as_view({'post': 'tanya'})
chatbot_rating = ChatbotViewSet.as_view({'post': 'rating'})

urlpatterns = [
    path('tanya/', chatbot_tanya, name='chatbot-tanya'),
    path('rating/', chatbot_rating, name='chatbot-rating'),
    path('status/<uuid:pelacakan_id>/', StatusKonsultasiView.as_view(), name='chatbot-status'),
]

urlpatterns += router.urls
