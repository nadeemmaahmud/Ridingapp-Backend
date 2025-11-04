from django.db import models
from users.models import CustomUser

class RidingEvent(models.Model):
    status_choices = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_events')
    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='driver_events')
    from_where = models.CharField(max_length=100)
    to_where = models.CharField(max_length=100)
    distance_km = models.FloatField()
    estimated_time_min = models.FloatField()
    charge_amount = models.FloatField()
    payment_method = models.CharField(max_length=50)
    payment_completed = models.BooleanField(default=False)
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, null=True, blank=True, default='pending', choices=status_choices)

    def __str__(self):
        return f"{self.from_where} to {self.to_where}"


class StripePayment(models.Model):
    payment_status_choices = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    riding_event = models.OneToOneField(RidingEvent, on_delete=models.CASCADE, related_name='stripe_payment')
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_charge_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20, choices=payment_status_choices, default='pending')
    payment_method_id = models.CharField(max_length=255, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} - {self.status}"

    class Meta:
        ordering = ['-created_at']
