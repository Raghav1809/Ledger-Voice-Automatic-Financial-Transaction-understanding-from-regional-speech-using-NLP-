from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum

class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', 'name']
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def total_credit(self):
        # Credit + Cash Out / Sales
        credit_sum = self.transactions.filter(transaction_type__in=['credit', 'sales']).aggregate(total=Sum('amount'))['total'] or 0.0
        return float(credit_sum)

    @property
    def total_payments(self):
        # Payment + Cash In
        payment_sum = self.transactions.filter(transaction_type__in=['payment', 'expense']).aggregate(total=Sum('amount'))['total'] or 0.0
        return float(payment_sum)

    @property
    def net_balance(self):
        # Outstanding credit owed by customer = total credit - total payments
        return self.total_credit - self.total_payments
