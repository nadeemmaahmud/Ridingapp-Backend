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
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, null=True, blank=True, default='pending', choices=status_choices)

    def __str__(self):
        return f"{self.from_where} to {self.to_where}"
