from django.contrib import admin
from .models import RidingEvent, StripePayment

@admin.register(RidingEvent)
class RidingEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'driver', 'from_where', 'to_where', 'distance_km', 'charge_amount', 'payment_method', 'payment_completed', 'status', 'created_at']
    list_filter = ['payment_completed', 'payment_method', 'status', 'created_at']
    search_fields = ['user__full_name', 'driver__full_name', 'from_where', 'to_where', 'stripe_payment_intent_id']
    readonly_fields = ['created_at', 'stripe_payment_intent_id']
    ordering = ['-created_at']
    list_editable = ['status']
    fieldsets = (
        ('Event Details', {
            'fields': ('user', 'driver', 'from_where', 'to_where')
        }),
        ('Trip Information', {
            'fields': ('distance_km', 'estimated_time_min', 'charge_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_completed', 'stripe_payment_intent_id')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    actions = ['mark_completed', 'mark_cancelled', 'mark_in_progress']
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        for event in queryset:
            if event.driver:
                event.driver.driver_is_available = True
                event.driver.save()
        self.message_user(request, f'{updated} events marked as completed.')
    mark_completed.short_description = "Mark selected events as completed"
    
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        for event in queryset:
            if event.driver:
                event.driver.driver_is_available = True
                event.driver.save()
        self.message_user(request, f'{updated} events marked as cancelled.')
    mark_cancelled.short_description = "Mark selected events as cancelled"
    
    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} events marked as in progress.')
    mark_in_progress.short_description = "Mark selected events as in progress"


@admin.register(StripePayment)
class StripePaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'riding_event', 'stripe_payment_intent_id', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['stripe_payment_intent_id', 'stripe_charge_id', 'customer_email', 'riding_event__from_where', 'riding_event__to_where']
    readonly_fields = ['created_at', 'updated_at', 'stripe_payment_intent_id', 'stripe_charge_id']
    ordering = ['-created_at']
