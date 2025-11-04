from rest_framework import serializers
from .models import RidingEvent
from users.models import CustomUser

class RidingEventSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    driver_email = serializers.EmailField(source='driver.email', read_only=True)
    
    class Meta:
        model = RidingEvent
        fields = [
            'id', 'user', 'driver', 'user_name', 'driver_name', 
            'user_email', 'driver_email', 'from_where', 'to_where',
            'distance_km', 'estimated_time_min', 'charge_amount',
            'payment_method', 'payment_completed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'user_name', 'driver_name', 'user_email', 'driver_email']

    def validate(self, data):
        user = data.get('user')
        driver = data.get('driver')
        
        if user and driver and user.id == driver.id:
            raise serializers.ValidationError("User and driver cannot be the same person.")
        
        if user and user.account_type != 'user':
            raise serializers.ValidationError("The user field must reference a user account type.")
        
        if driver and driver.account_type != 'driver':
            raise serializers.ValidationError("The driver field must reference a driver account type.")
        
        if data.get('distance_km') and data['distance_km'] < 0:
            raise serializers.ValidationError("Distance cannot be negative.")
        
        if data.get('estimated_time_min') and data['estimated_time_min'] < 0:
            raise serializers.ValidationError("Estimated time cannot be negative.")
        
        if data.get('charge_amount') and data['charge_amount'] < 0:
            raise serializers.ValidationError("Charge amount cannot be negative.")
        
        return data

class CreateRidingEventSerializer(serializers.Serializer):
    from_where = serializers.CharField(max_length=100, required=True)
    to_where = serializers.CharField(max_length=100, required=True)
    payment_method = serializers.ChoiceField(
        choices=['credit_card', 'debit_card', 'cash'],
        required=True
    )
    
    def validate(self, data):
        if data['from_where'] == data['to_where']:
            raise serializers.ValidationError("Origin and destination cannot be the same.")
        return data
