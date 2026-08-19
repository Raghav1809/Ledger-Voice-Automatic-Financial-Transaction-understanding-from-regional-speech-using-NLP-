from rest_framework import serializers
from .models import Reminder
from customers.serializers import CustomerSerializer

class ReminderSerializer(serializers.ModelSerializer):
    customer_detail = CustomerSerializer(source='customer', read_only=True)
    computed_status = serializers.ReadOnlyField(source='current_status')

    class Meta:
        model = Reminder
        fields = [
            'id', 'customer', 'customer_detail', 'title', 'amount',
            'due_date', 'status', 'computed_status', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
