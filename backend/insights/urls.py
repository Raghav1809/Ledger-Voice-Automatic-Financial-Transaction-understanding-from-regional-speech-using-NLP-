from django.urls import path
from .views import InsightSummaryView, AdvancedAnalyticsView

urlpatterns = [
    path('summary/', InsightSummaryView.as_view(), name='insight_summary'),
    path('analytics/', AdvancedAnalyticsView.as_view(), name='advanced_analytics'),
]
