from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Reminder
from .serializers import ReminderSerializer

class ReminderViewSet(viewsets.ModelViewSet):
    serializer_class = ReminderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'customer__name', 'notes']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']

    def get_queryset(self):
        queryset = Reminder.objects.filter(user=self.request.user)
        
        # Category filter: today, upcoming, missed
        category = self.request.query_params.get('category')
        today = timezone.now().date()

        if category == 'today':
            queryset = queryset.filter(due_date=today, status='pending')
        elif category == 'upcoming':
            queryset = queryset.filter(due_date__gt=today, status='pending')
        elif category == 'missed':
            queryset = queryset.filter(due_date__lt=today, status='pending')

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_complete(self, request, pk=None):
        reminder = self.get_object()
        reminder.status = 'completed' if reminder.status != 'completed' else 'pending'
        reminder.save()
        return Response({
            'id': reminder.id,
            'status': reminder.status,
            'computed_status': reminder.current_status
        }, status=status.HTTP_200_OK)
