from rest_framework import serializers
from .models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ['id', 'product_name', 'unit', 'price', 'quantity', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_product_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Product name cannot be empty.")
        return value.strip().title()

    def validate_price(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_quantity(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_unit(self, value):
        valid_units = [choice[0] for choice in InventoryItem.UNIT_CHOICES]
        if value not in valid_units:
            raise serializers.ValidationError(
                f"Invalid unit '{value}'. Must be one of: {', '.join(valid_units)}"
            )
        return value

    def validate(self, attrs):
        """Case-insensitive duplicate check scoped to the authenticated user."""
        user = self.context['request'].user
        product_name = attrs.get('product_name', '').strip().title()

        # Check for duplicate product name (case-insensitive) for this user
        qs = InventoryItem.objects.filter(
            user=user,
            product_name__iexact=product_name
        )

        # If updating, exclude the current instance from the duplicate check
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                'product_name': f"Product '{product_name}' already exists in your inventory."
            })

        return attrs

    def create(self, validated_data):
        user = validated_data.pop('user', None) or self.context['request'].user
        return InventoryItem.objects.create(user=user, **validated_data)
