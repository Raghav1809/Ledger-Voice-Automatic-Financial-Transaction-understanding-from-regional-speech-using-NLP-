from django.db import models
from django.contrib.auth.models import User
from customers.models import Customer
from django.utils import timezone

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit (Gave / Loaned)'),
        ('payment', 'Payment (Received / Got)'),
        ('cash_in', 'Cash In'),
        ('cash_out', 'Cash Out'),
        ('sales', 'Sales'),
        ('expense', 'Expense'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('settled', 'Settled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    customer_name_raw = models.CharField(max_length=150, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='credit')
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    # Stores itemized list for sales transactions:
    # [{"name": "Sugar", "qty": 20, "unit": "kg", "price": 100}, ...]
    items_data = models.JSONField(blank=True, null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        c_name = self.customer.name if self.customer else (self.customer_name_raw or 'Sales')
        return f"{self.transaction_type.upper()}: {self.amount} - {c_name} ({self.date})"
