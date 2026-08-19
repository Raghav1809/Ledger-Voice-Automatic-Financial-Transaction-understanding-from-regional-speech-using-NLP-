from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import InventoryItem
from .serializers import InventoryItemSerializer


# Unit conversion factors to a base unit within each unit family
UNIT_CONVERSIONS = {
    # Mass: base = grams
    'kg': ('mass', 1000.0),
    'g': ('mass', 1.0),
    # Volume: base = ml
    'litre': ('volume', 1000.0),
    'ml': ('volume', 1.0),
}


def convert_inventory_price(inventory_item, requested_unit):
    """
    Convert an inventory item's price to a different unit within the same family.
    Returns (converted_price_per_unit, True) if conversion is possible,
    or (original_price, False) if units are incompatible.
    """
    inv_unit = inventory_item.unit
    inv_price = float(inventory_item.price)

    if inv_unit == requested_unit:
        return inv_price, True

    inv_conv = UNIT_CONVERSIONS.get(inv_unit)
    req_conv = UNIT_CONVERSIONS.get(requested_unit)

    if inv_conv and req_conv and inv_conv[0] == req_conv[0]:
        # Same family: price_per_requested = price_per_inv * (inv_factor / req_factor)
        # e.g. ₹45/kg → per gram = 45 * (1000 / 1) ... wait, we need price per requested unit
        # price per base unit = inv_price / inv_factor
        # price per requested unit = (inv_price / inv_factor) * req_factor
        price_per_base = inv_price / inv_conv[1]
        converted_price = price_per_base * req_conv[1]
        return round(converted_price, 2), True

    return inv_price, False


class InventoryViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for InventoryItem.
    All operations are scoped to the authenticated user.
    """
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product_name']
    ordering_fields = ['product_name', 'price', 'created_at', 'updated_at']
    ordering = ['product_name']

    def get_queryset(self):
        return InventoryItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='lookup')
    def lookup(self, request):
        """
        Lookup inventory price by product name (case-insensitive).
        GET /api/inventory/lookup/?product=sugar&unit=kg
        Returns the matching inventory item and optionally converts price to requested unit.
        """
        product_name = request.query_params.get('product', '').strip()
        requested_unit = request.query_params.get('unit', '').strip().lower()

        if not product_name:
            return Response(
                {'error': 'Product name is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        item = InventoryItem.objects.filter(
            user=request.user,
            product_name__iexact=product_name
        ).first()

        if not item:
            return Response(
                {'found': False, 'product': product_name},
                status=status.HTTP_200_OK
            )

        data = InventoryItemSerializer(item).data
        data['found'] = True

        # If a unit was requested and it differs, attempt conversion
        if requested_unit and requested_unit != item.unit:
            converted_price, success = convert_inventory_price(item, requested_unit)
            if success:
                data['converted_price'] = converted_price
                data['converted_unit'] = requested_unit
                data['conversion_applied'] = True
            else:
                data['conversion_applied'] = False

        return Response(data, status=status.HTTP_200_OK)
