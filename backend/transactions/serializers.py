from rest_framework import serializers
from .models import Transaction
from customers.models import Customer
from customers.serializers import CustomerSerializer


class TransactionSerializer(serializers.ModelSerializer):
    customer_detail = CustomerSerializer(source='customer', read_only=True)
    customer_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'customer', 'customer_name', 'customer_name_raw', 'customer_detail',
            'amount', 'transaction_type', 'date', 'due_date', 'description',
            'status', 'items_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'due_date' in data and (data['due_date'] == '' or data['due_date'] is None):
                data['due_date'] = None
            if 'date' in data and (data['date'] == '' or data['date'] is None):
                data.pop('date')
            # Auto-compute amount from items_data if amount is 0 or missing
            items = data.get('items_data')
            if items and isinstance(items, list):
                try:
                    computed = sum(
                        float(i.get('qty', 1)) * float(i.get('price', 0))
                        for i in items
                    )
                    if not data.get('amount') or float(data.get('amount', 0)) == 0:
                        data['amount'] = round(computed, 2)
                except (TypeError, ValueError):
                    pass
        return super().to_internal_value(data)

    def create(self, validated_data):
        customer_name = validated_data.pop('customer_name', None)
        # 'user' is injected by perform_create via serializer.save(user=...)
        user = validated_data.pop('user', None) or self.context['request'].user

        tx_type = validated_data.get('transaction_type', 'credit')
        is_sales = tx_type == 'sales'

        if not is_sales:
            # For non-sales transactions, resolve customer
            if customer_name and not validated_data.get('customer'):
                clean_name = customer_name.strip()
                customer = Customer.objects.filter(user=user, name__iexact=clean_name).first()
                if not customer:
                    customer = Customer.objects.create(user=user, name=clean_name)
                validated_data['customer'] = customer
                validated_data['customer_name_raw'] = customer.name
            elif validated_data.get('customer'):
                validated_data['customer_name_raw'] = validated_data['customer'].name
        else:
            # Sales: customer is optional — store name only if provided
            if customer_name and customer_name.strip():
                validated_data['customer_name_raw'] = customer_name.strip()

        if tx_type == 'credit' and 'status' not in validated_data:
            validated_data['status'] = 'pending'

        transaction = Transaction.objects.create(user=user, **validated_data)

        # Repayment logic: update existing PENDING credit transactions for this customer to SETTLED
        if tx_type == 'payment' and transaction.customer:
            pending_credits = Transaction.objects.filter(
                user=user,
                customer=transaction.customer,
                transaction_type='credit',
                status='pending'
            ).order_by('date', 'created_at')

            remaining_payment = float(transaction.amount)
            for credit_tx in pending_credits:
                if remaining_payment <= 0:
                    break
                credit_amt = float(credit_tx.amount)
                if remaining_payment >= credit_amt:
                    credit_tx.status = 'settled'
                    credit_tx.save()
                    remaining_payment -= credit_amt

        # Auto-create reminder if due_date is present
        if transaction.due_date and transaction.customer:
            from reminders.models import Reminder
            Reminder.objects.get_or_create(
                user=user,
                customer=transaction.customer,
                due_date=transaction.due_date,
                defaults={
                    'title': f"Payment Due from {transaction.customer.name}",
                    'amount': transaction.amount,
                    'notes': f"Auto-created from transaction #{transaction.id}: {transaction.description or 'Due payment'}"
                }
            )

        return transaction

    def update(self, instance, validated_data):
        customer_name = validated_data.pop('customer_name', None)
        validated_data.pop('user', None)  # remove injected user to avoid duplicate kwarg
        user = self.context['request'].user

        tx_type = validated_data.get('transaction_type', instance.transaction_type)
        if tx_type != 'sales' and customer_name and not validated_data.get('customer'):
            clean_name = customer_name.strip()
            customer = Customer.objects.filter(user=user, name__iexact=clean_name).first()
            if not customer:
                customer = Customer.objects.create(user=user, name=clean_name)
            validated_data['customer'] = customer
            validated_data['customer_name_raw'] = customer.name
        elif tx_type == 'sales' and customer_name and customer_name.strip():
            validated_data['customer_name_raw'] = customer_name.strip()

        return super().update(instance, validated_data)