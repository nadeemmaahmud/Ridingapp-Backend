from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from math import radians, cos, sin, asin, sqrt
from .models import ChatRoom, ChatMessage, DriverLocation
from .serializers import ChatRoomSerializer, ChatMessageSerializer, DriverLocationSerializer, NearbyDriverSerializer
from maps.models import RidingEvent


class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(
            riding_event__user=user
        ) | ChatRoom.objects.filter(
            riding_event__driver=user
        )
    
    def check_chat_access(self, chat_room):
        event = chat_room.riding_event
        if self.request.user != event.user and self.request.user != event.driver:
            return False
        return True

    @action(detail=False, methods=['get'], url_path='by-event/(?P<event_id>[^/.]+)')
    def by_event(self, request, event_id=None):
        event = get_object_or_404(RidingEvent, id=event_id)
        if request.user != event.user and request.user != event.driver:
            return Response(
                {'error': 'You do not have access to this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        chat_room, created = ChatRoom.objects.get_or_create(riding_event=event)
        serializer = self.get_serializer(chat_room)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        chat_room = self.get_object()
        if not self.check_chat_access(chat_room):
            return Response(
                {'error': 'You do not have access to this chat room'},
                status=status.HTTP_403_FORBIDDEN
            )
        message_text = request.data.get('message')
        if not message_text:
            return Response(
                {'error': 'Message content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        message = ChatMessage.objects.create(
            chat_room=chat_room,
            sender=request.user,
            message=message_text
        )
        serializer = ChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        chat_room = self.get_object()
        if not self.check_chat_access(chat_room):
            return Response(
                {'error': 'You do not have access to this chat room'},
                status=status.HTTP_403_FORBIDDEN
            )
        messages = chat_room.messages.all()
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = ChatMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)


class DriverLocationViewSet(viewsets.ModelViewSet):
    serializer_class = DriverLocationSerializer
    permission_classes = [IsAuthenticated]
    queryset = DriverLocation.objects.all()

    @action(detail=False, methods=['post'])
    def update_location(self, request):
        if not hasattr(request.user, 'account_type') or request.user.account_type != 'driver':
            return Response(
                {'error': 'Only drivers can update their location'},
                status=status.HTTP_403_FORBIDDEN
            )
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        is_available = request.data.get('is_available', True)
        if latitude is None or longitude is None:
            return Response(
                {'error': 'Latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        location, created = DriverLocation.objects.update_or_create(
            driver=request.user,
            defaults={
                'latitude': latitude,
                'longitude': longitude,
                'is_available': is_available
            }
        )
        serializer = self.get_serializer(location)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius_km = float(request.query_params.get('radius_km', 10))
        if not latitude or not longitude:
            return Response(
                {'error': 'Latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        latitude = float(latitude)
        longitude = float(longitude)
        available_drivers = DriverLocation.objects.filter(
            is_available=True
        ).select_related('driver')
        nearby_drivers = []
        for driver_loc in available_drivers:
            distance = self.haversine(
                latitude, longitude,
                driver_loc.latitude, driver_loc.longitude
            )
            if distance <= radius_km:
                nearby_drivers.append({
                    'driver': driver_loc.driver,
                    'distance_km': round(distance, 2),
                    'latitude': driver_loc.latitude,
                    'longitude': driver_loc.longitude,
                    'is_available': driver_loc.is_available
                })
        nearby_drivers.sort(key=lambda x: x['distance_km'])
        serializer = NearbyDriverSerializer(nearby_drivers, many=True)
        return Response(serializer.data)

    def haversine(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km
