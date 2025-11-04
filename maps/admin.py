from django.contrib import admin
from .models import RidingEvent, StripePayment

@admin.register(RidingEvent)
class RidingEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'driver', 'from_where', 'to_where', 'distance_km', 'charge_amount', 'payment_method', 'payment_completed', 'status', 'created_at']
    list_filter = ['payment_completed', 'payment_method', 'status', 'created_at']
    search_fields = ['user__full_name', 'driver__full_name', 'from_where', 'to_where', 'stripe_payment_intent_id']
    readonly_fields = ['created_at', 'stripe_payment_intent_id']
    ordering = ['-created_at']


@admin.register(StripePayment)
class StripePaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'riding_event', 'stripe_payment_intent_id', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['stripe_payment_intent_id', 'stripe_charge_id', 'customer_email', 'riding_event__from_where', 'riding_event__to_where']
    readonly_fields = ['created_at', 'updated_at', 'stripe_payment_intent_id', 'stripe_charge_id']
    ordering = ['-created_at']
