from django.urls import path
from .views import SpeechParseView

urlpatterns = [
    path('parse/', SpeechParseView.as_view(), name='voice_parse'),
]
