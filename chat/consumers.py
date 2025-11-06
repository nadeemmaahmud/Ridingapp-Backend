import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from .models import ChatRoom, ChatMessage, DriverLocation
from maps.models import RidingEvent
from math import radians, cos, sin, asin, sqrt

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.riding_event_id = self.scope['url_route']['kwargs']['riding_event_id']
        self.room_group_name = f'chat_ride_{self.riding_event_id}'
        self.user = self.scope['user']
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        if not await self.can_access_chat():
            await self.close()
            return
        if await self.is_event_completed():
            await self.close()
            return
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        messages = await self.get_chat_history()
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': messages
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
            return
        message_type = data.get('type', 'chat_message')
        if message_type == 'chat_message':
            message = data['message']
            if await self.is_event_completed():
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Chat is disabled. This riding event has been completed.'
                }))
                await self.close()
                return
            if not await self.can_access_chat():
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You do not have access to this chat room'
                }))
                await self.close()
                return
            chat_message = await self.save_message(message)
            if chat_message is None:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to send message'
                }))
                return
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender_name': await self.get_sender_name(),
                    'timestamp': str(chat_message.timestamp),
                    'message_id': chat_message.id
                }
            )
        elif message_type == 'mark_read':
            message_id = data.get('message_id')
            if await self.can_access_chat():
                await self.mark_message_read(message_id)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id']
        }))

    @database_sync_to_async
    def can_access_chat(self):
        try:
            event = RidingEvent.objects.get(id=self.riding_event_id)
            return self.user == event.user or self.user == event.driver
        except RidingEvent.DoesNotExist:
            return False

    @database_sync_to_async
    def is_event_completed(self):
        try:
            event = RidingEvent.objects.get(id=self.riding_event_id)
            return event.status == 'completed'
        except RidingEvent.DoesNotExist:
            return True

    @database_sync_to_async
    def get_chat_history(self):
        try:
            chat_room = ChatRoom.objects.get(riding_event_id=self.riding_event_id)
            messages = chat_room.messages.all()[:50]
            return [{
                'id': msg.id,
                'message': msg.message,
                'sender_id': msg.sender.id,
                'sender_name': msg.sender.get_full_name() if hasattr(msg.sender, 'get_full_name') else str(msg.sender),
                'timestamp': str(msg.timestamp),
                'is_read': msg.is_read
            } for msg in messages]
        except ChatRoom.DoesNotExist:
            return []

    @database_sync_to_async
    def save_message(self, message):
        try:
            event = RidingEvent.objects.get(id=self.riding_event_id)
            if event.status == 'completed':
                return None
            if self.user != event.user and self.user != event.driver:
                return None
            chat_room, _ = ChatRoom.objects.get_or_create(
                riding_event_id=self.riding_event_id
            )
            chat_message = ChatMessage.objects.create(
                chat_room=chat_room,
                sender=self.user,
                message=message
            )
            return chat_message
        except RidingEvent.DoesNotExist:
            return None
        except Exception:
            return None

    @database_sync_to_async
    def get_sender_name(self):
        if hasattr(self.user, 'get_full_name'):
            return self.user.get_full_name()
        return str(self.user)

    @database_sync_to_async
    def mark_message_read(self, message_id):
        try:
            message = ChatMessage.objects.get(id=message_id)
            if message.chat_room.riding_event_id != int(self.riding_event_id):
                return
            event = message.chat_room.riding_event
            if self.user != event.user and self.user != event.driver:
                return
            if message.sender != self.user:
                message.is_read = True
                message.save()
        except ChatMessage.DoesNotExist:
            pass
        except Exception:
            pass

class DriverLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if hasattr(self.user, 'account_type') and self.user.account_type == 'driver':
            self.room_group_name = f'driver_location_{self.user.id}'
        else:
            self.room_group_name = 'nearby_drivers'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        if message_type == 'update_location' and self.user.account_type == 'driver':
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            is_available = data.get('is_available', True)
            await self.update_driver_location(latitude, longitude, is_available)
            await self.channel_layer.group_send(
                'nearby_drivers',
                {
                    'type': 'location_update',
                    'driver_id': self.user.id,
                    'latitude': latitude,
                    'longitude': longitude,
                    'is_available': is_available,
                    'driver_name': await self.get_driver_name(),
                    'car_name': await self.get_car_name(),
                    'car_color': await self.get_car_color()
                }
            )
        elif message_type == 'request_nearby_drivers':
            user_lat = data.get('latitude')
            user_lng = data.get('longitude')
            radius_km = data.get('radius_km', 10)
            nearby_drivers = await self.get_nearby_drivers(user_lat, user_lng, radius_km)
            await self.send(text_data=json.dumps({
                'type': 'nearby_drivers',
                'drivers': nearby_drivers
            }))

    async def location_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'driver_id': event['driver_id'],
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'is_available': event['is_available'],
            'driver_name': event['driver_name'],
            'car_name': event['car_name'],
            'car_color': event['car_color']
        }))

    @database_sync_to_async
    def update_driver_location(self, latitude, longitude, is_available):
        DriverLocation.objects.update_or_create(
            driver=self.user,
            defaults={
                'latitude': latitude,
                'longitude': longitude,
                'is_available': is_available
            }
        )

    @database_sync_to_async
    def get_nearby_drivers(self, user_lat, user_lng, radius_km):
        all_drivers = DriverLocation.objects.filter(is_available=True).select_related('driver')
        nearby = []
        for driver_loc in all_drivers:
            distance = self.haversine(user_lat, user_lng, driver_loc.latitude, driver_loc.longitude)
            if distance <= radius_km:
                nearby.append({
                    'driver_id': driver_loc.driver.id,
                    'driver_name': driver_loc.driver.get_full_name() if hasattr(driver_loc.driver, 'get_full_name') else str(driver_loc.driver),
                    'latitude': driver_loc.latitude,
                    'longitude': driver_loc.longitude,
                    'distance_km': round(distance, 2),
                    'car_name': getattr(driver_loc.driver, 'car_name', ''),
                    'car_color': getattr(driver_loc.driver, 'car_color', ''),
                    'rating': getattr(driver_loc.driver, 'rating', 0)
                })
        return sorted(nearby, key=lambda x: x['distance_km'])

    def haversine(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km

    @database_sync_to_async
    def get_driver_name(self):
        if hasattr(self.user, 'get_full_name'):
            return self.user.get_full_name()
        return str(self.user)

    @database_sync_to_async
    def get_car_name(self):
        return getattr(self.user, 'car_name', '')

    @database_sync_to_async
    def get_car_color(self):
        return getattr(self.user, 'car_color', '')
