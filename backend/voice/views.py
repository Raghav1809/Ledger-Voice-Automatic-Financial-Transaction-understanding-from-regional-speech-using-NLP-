from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .parsers import parse_speech_transcript


class SpeechParseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _enrich_items_with_inventory(self, items, user):
        """
        Post-process parsed sales items with inventory price lookup.
        Pricing priority:
          1. Explicit price from voice (item already has price > 0)
          2. Inventory price (case-insensitive product lookup)
          3. Missing — frontend will ask user during confirmation
        """
        if not items:
            return items

        from inventory.models import InventoryItem
        from inventory.views import convert_inventory_price, UNIT_CONVERSIONS

        for item in items:
            if item.get('price', 0) > 0 and item.get('total', 0) > 0:
                # RULE 3: Explicit voice price always wins
                item['price_source'] = 'voice'
            else:
                # Try inventory lookup (case-insensitive)
                inv_item = InventoryItem.objects.filter(
                    user=user,
                    product_name__iexact=item.get('name', '').strip()
                ).first()

                if inv_item:
                    item_unit = item.get('unit', 'pcs')
                    inv_unit = inv_item.unit
                    inv_price = float(inv_item.price)

                    # Check if units match or can be converted
                    if item_unit == inv_unit:
                        # Direct match
                        unit_price = inv_price
                    else:
                        # Attempt unit conversion (kg↔g, litre↔ml)
                        converted_price, success = convert_inventory_price(inv_item, item_unit)
                        if success:
                            unit_price = converted_price
                        else:
                            # Incompatible units — use inventory price as-is with a warning
                            unit_price = inv_price
                            item['unit_mismatch'] = True
                            item['inventory_unit'] = inv_unit

                    qty = float(item.get('qty', 1))
                    item['price'] = round(unit_price, 2)
                    item['total'] = round(unit_price * qty, 2)
                    item['price_source'] = 'inventory'
                    item['inventory_unit'] = inv_item.unit
                    item['inventory_price'] = float(inv_item.price)
                else:
                    # RULE 5 & 6: Product not in inventory, no price — mark as missing
                    item['price_source'] = 'missing'

        return items

    def post(self, request):
        transcript = request.data.get('transcript', '')

        if not transcript:
            return Response(
                {'error': 'Speech transcript is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        parsed_data = parse_speech_transcript(transcript)

        # Enrich sales items with inventory prices
        if parsed_data.get('items') and isinstance(parsed_data['items'], list):
            parsed_data['items'] = self._enrich_items_with_inventory(
                parsed_data['items'], request.user
            )

            # Recalculate total amount from enriched items
            total = sum(
                float(item.get('total', 0))
                for item in parsed_data['items']
            )
            if total > 0:
                parsed_data['amount'] = round(total, 2)

        return Response(parsed_data, status=status.HTTP_200_OK)
