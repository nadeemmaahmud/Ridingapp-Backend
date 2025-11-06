from rest_framework import serializers
from .models import ChatRoom, ChatMessage, DriverLocation
from users.serializers import BasicUserSerializer

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_phone = serializers.CharField(source='sender.phone_number', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'chat_room', 'sender', 'sender_name', 'sender_phone', 
                  'message', 'timestamp', 'is_read']
        read_only_fields = ['id', 'timestamp', 'sender_name', 'sender_phone']
    
    def get_sender_name(self, obj):
        if hasattr(obj.sender, 'full_name') and obj.sender.full_name:
            return obj.sender.full_name
        return obj.sender.phone_number or str(obj.sender)

class ChatRoomSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'riding_event', 'room_name', 'created_at', 
                  'updated_at', 'messages', 'last_message']
        read_only_fields = ['id', 'room_name', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return ChatMessageSerializer(last_msg).data
        return None

class DriverLocationSerializer(serializers.ModelSerializer):
    driver_info = BasicUserSerializer(source='driver', read_only=True)
    
    class Meta:
        model = DriverLocation
        fields = ['id', 'driver', 'driver_info', 'latitude', 'longitude', 
                  'is_available', 'last_updated']
        read_only_fields = ['id', 'last_updated']

class NearbyDriverSerializer(serializers.Serializer):
    driver = BasicUserSerializer()
    distance_km = serializers.FloatField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    is_available = serializers.BooleanField()
