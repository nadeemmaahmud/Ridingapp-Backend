from django.db import models
from users.models import CustomUser
from maps.models import RidingEvent

class ChatRoom(models.Model):
    riding_event = models.OneToOneField(
        RidingEvent,
        on_delete=models.CASCADE,
        related_name='chat_room'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat for Event #{self.riding_event.id}"

    @property
    def room_name(self):
        return f"ride_{self.riding_event.id}"
    
    def has_access(self, user):
        return (user == self.riding_event.user or 
                user == self.riding_event.driver)
    
    def get_participants(self):
        return [self.riding_event.user, self.riding_event.driver]

class ChatMessage(models.Model):
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.phone_number}: {self.message[:50]}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.chat_room.has_access(self.sender):
            raise ValidationError(
                'Sender does not have access to this chat room. '
                'Only the user and driver of the riding event can send messages.'
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class DriverLocation(models.Model):
    driver = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='current_location',
        limit_choices_to={'account_type': 'driver'}
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_available = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Driver Location"
        verbose_name_plural = "Driver Locations"

    def __str__(self):
        return f"{self.driver.phone_number} - ({self.latitude}, {self.longitude})"
