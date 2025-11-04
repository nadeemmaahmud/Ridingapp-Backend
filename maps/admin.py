from django.contrib import admin
from .models import RidingEvent

@admin.register(RidingEvent)
class RidingEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'driver', 'from_where', 'to_where', 'distance_km', 'charge_amount', 'payment_completed', 'created_at']
    list_filter = ['payment_completed', 'payment_method', 'created_at']
    search_fields = ['user__full_name', 'driver__full_name', 'from_where', 'to_where']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
