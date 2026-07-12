from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import ChatbotViewSet, PercakapanChatbotViewSet

router = DefaultRouter()
router.register('percakapan', PercakapanChatbotViewSet, basename='percakapanchatbot')

chatbot_tanya = ChatbotViewSet.as_view({'post': 'tanya'})
chatbot_rating = ChatbotViewSet.as_view({'post': 'rating'})

urlpatterns = [
    path('tanya/', chatbot_tanya, name='chatbot-tanya'),
    path('rating/', chatbot_rating, name='chatbot-rating'),
]

urlpatterns += router.urls
