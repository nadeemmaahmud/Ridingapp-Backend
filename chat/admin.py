from django.contrib import admin
from .models import ChatRoom, ChatMessage, DriverLocation


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'riding_event', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['riding_event__id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat_room', 'sender', 'message', 'timestamp', 'is_read']
    list_filter = ['timestamp', 'is_read']
    search_fields = ['message', 'sender__phone_number']
    readonly_fields = ['timestamp']


@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display = ['driver', 'latitude', 'longitude', 'is_available', 'last_updated']
    list_filter = ['is_available', 'last_updated']
    search_fields = ['driver__phone_number']
    readonly_fields = ['last_updated']
