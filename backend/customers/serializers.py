from rest_framework import serializers
from .models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    total_credit = serializers.ReadOnlyField()
    total_payments = serializers.ReadOnlyField()
    net_balance = serializers.ReadOnlyField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'email', 'address', 'notes', 'total_credit', 'total_payments', 'net_balance', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        user = self.context['request'].user
        instance = self.instance
        if instance:
            if Customer.objects.filter(user=user, name__iexact=value).exclude(id=instance.id).exists():
                raise serializers.ValidationError("A customer with this name already exists.")
        else:
            if Customer.objects.filter(user=user, name__iexact=value).exists():
                raise serializers.ValidationError("A customer with this name already exists.")
        return value
