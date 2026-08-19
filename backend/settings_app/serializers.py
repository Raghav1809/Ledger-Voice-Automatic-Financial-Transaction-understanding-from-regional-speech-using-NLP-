from rest_framework import serializers
from .models import UserSettings

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['theme', 'currency', 'language', 'enable_notifications', 'sound_effects', 'upi_link', 'upi_id', 'updated_at']
        read_only_fields = ['language', 'updated_at']
