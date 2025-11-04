from rest_framework import serializers
from .models import RidingEvent, StripePayment
from users.models import CustomUser

class StripePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StripePayment
        fields = [
            'id', 'riding_event', 'stripe_payment_intent_id', 
            'stripe_charge_id', 'amount', 'currency', 'status',
            'payment_method_id', 'customer_email', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'stripe_payment_intent_id', 'stripe_charge_id',
            'created_at', 'updated_at'
        ]


class RidingEventSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    driver_name = serializers.CharField(source='driver.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    driver_email = serializers.EmailField(source='driver.email', read_only=True)
    stripe_payment = StripePaymentSerializer(read_only=True)
    
    class Meta:
        model = RidingEvent
        fields = [
            'id', 'user', 'driver', 'user_name', 'driver_name', 
            'user_email', 'driver_email', 'from_where', 'to_where',
            'distance_km', 'estimated_time_min', 'charge_amount',
            'payment_method', 'payment_completed', 'stripe_payment_intent_id',
            'created_at', 'stripe_payment', 'status'
        ]
        read_only_fields = [
            'id', 'created_at', 'user_name', 'driver_name', 
            'user_email', 'driver_email', 'stripe_payment'
        ]

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
        choices=['credit_card', 'debit_card', 'cash', 'stripe'],
        required=True
    )
    
    def validate(self, data):
        if data['from_where'] == data['to_where']:
            raise serializers.ValidationError("Origin and destination cannot be the same.")
        return data


class CreatePaymentIntentSerializer(serializers.Serializer):
    riding_event_id = serializers.IntegerField(required=True)
    
    def validate_riding_event_id(self, value):
        try:
            riding_event = RidingEvent.objects.get(id=value)
            if riding_event.payment_method != 'stripe':
                raise serializers.ValidationError(
                    "This riding event does not use Stripe as payment method."
                )
            if riding_event.payment_completed:
                raise serializers.ValidationError(
                    "Payment for this riding event is already completed."
                )
        except RidingEvent.DoesNotExist:
            raise serializers.ValidationError("Riding event not found.")
        return value
