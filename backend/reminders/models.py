from django.db import models
from django.contrib.auth.models import User
from customers.models import Customer
from django.utils import timezone

class Reminder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-created_at']

    def __str__(self):
        return f"Reminder for {self.customer.name}: {self.title} due {self.due_date}"

    @property
    def current_status(self):
        if self.status == 'completed':
            return 'completed'
        today = timezone.now().date()
        if self.due_date < today:
            return 'missed'
        return 'pending'
