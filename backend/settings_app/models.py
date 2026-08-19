from django.db import models
from django.contrib.auth.models import User

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='app_settings')
    theme = models.CharField(max_length=20, default='light')
    currency = models.CharField(max_length=10, default='INR (₹)')
    language = models.CharField(max_length=10, default='en') # Locked to English
    enable_notifications = models.BooleanField(default=True)
    sound_effects = models.BooleanField(default=True)
    upi_link = models.CharField(max_length=500, blank=True, null=True)
    upi_id = models.CharField(max_length=100, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings for {self.user.username}"
