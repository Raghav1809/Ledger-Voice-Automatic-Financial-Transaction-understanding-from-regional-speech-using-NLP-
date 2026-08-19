from django.db import models
from django.contrib.auth.models import User


class InventoryItem(models.Model):
    """
    Stores a user's default product/price catalog.
    Inventory is optional — users can sell products not in inventory.
    """
    UNIT_CHOICES = (
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('litre', 'Litre'),
        ('ml', 'Millilitre'),
        ('pcs', 'Piece'),
        ('dozen', 'Dozen'),
        ('packet', 'Packet'),
        ('box', 'Box'),
        ('bag', 'Bag'),
        ('bundle', 'Bundle'),
        ('mtr', 'Metre'),
        ('ft', 'Feet'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory_items')
    product_name = models.CharField(max_length=150)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pcs')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product_name']
        unique_together = ('user', 'product_name')

    def __str__(self):
        return f"{self.product_name} — ₹{self.price}/{self.unit} ({self.user.username})"

    def save(self, *args, **kwargs):
        # Store product_name in title case for consistency
        if self.product_name:
            self.product_name = self.product_name.strip().title()
        super().save(*args, **kwargs)
