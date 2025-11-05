import os
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from .models import RidingEvent, StripePayment
from .serializers import (
    RidingEventSerializer, 
    CreateRidingEventSerializer, 
    CreatePaymentIntentSerializer,
    StripePaymentSerializer
)
from .stripe_utils import (
    create_payment_intent, 
    confirm_payment_intent, 
    construct_webhook_event
)
from users.models import CustomUser
from users.serializers import DriverSerializer

try:
    import googlemaps
    gmaps_available = True
    gmaps_client = None
except ImportError:
    gmaps_available = False
    gmaps_client = None

def get_gmaps_client():
    global gmaps_client
    if not gmaps_available:
        return None
    if gmaps_client is None:
        key = getattr(settings, 'GOOGLE_MAPS_API_KEY', os.environ.get('GOOGLE_MAPS_API_KEY'))
        if key:
            gmaps_client = googlemaps.Client(key=key)
    return gmaps_client

class AvailableDriversView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DriverSerializer
    
    def get_queryset(self):
        return CustomUser.objects.filter(
            account_type='driver',
            is_verified=True,
            driver_is_available=True
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        
        return Response({
            'message': 'Available drivers retrieved successfully',
            'count': queryset.count(),
            'drivers': serializer.data
        }, status=status.HTTP_200_OK)

class CreateRidingEventView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.account_type != 'user':
            return Response({
                'error': 'Only users can create riding events'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateRidingEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        driver_id = serializer.validated_data['driver_id']
        from_where = serializer.validated_data['from_where']
        to_where = serializer.validated_data['to_where']
        payment_method = serializer.validated_data['payment_method']

        try:
            driver = CustomUser.objects.get(id=driver_id)
            
            if not driver.driver_is_available:
                return Response({
                    'error': 'This driver is currently unavailable'
                }, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Driver not found'
            }, status=status.HTTP_404_NOT_FOUND)

        client = get_gmaps_client()
        if not client:
            return Response({
                'error': 'Google Maps service is not available'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            from_loc = client.geocode(from_where)
            to_loc = client.geocode(to_where)

            if not from_loc or not to_loc:
                return Response({
                    'error': 'Could not geocode one or both locations'
                }, status=status.HTTP_400_BAD_REQUEST)

            lat_from = from_loc[0]['geometry']['location']['lat']
            lng_from = from_loc[0]['geometry']['location']['lng']
            lat_to = to_loc[0]['geometry']['location']['lat']
            lng_to = to_loc[0]['geometry']['location']['lng']

            distance_result = client.distance_matrix(
                origins=[(lat_from, lng_from)],
                destinations=[(lat_to, lng_to)],
                mode='driving',
                units='metric'
            )

            if distance_result['rows'][0]['elements'][0]['status'] != 'OK':
                return Response({
                    'error': 'Could not calculate distance'
                }, status=status.HTTP_400_BAD_REQUEST)

            distance_km = distance_result['rows'][0]['elements'][0]['distance']['value'] / 1000.0
            duration_sec = distance_result['rows'][0]['elements'][0]['duration']['value']
            estimated_time_min = duration_sec / 60.0

            charge_amount = distance_km * 10.0

            riding_event = RidingEvent.objects.create(
                user=request.user,
                driver=driver,
                from_where=from_where,
                to_where=to_where,
                distance_km=round(distance_km, 2),
                estimated_time_min=round(estimated_time_min, 2),
                charge_amount=round(charge_amount, 2),
                payment_method=payment_method,
                payment_completed=False
            )
            
            driver.driver_is_available = False
            driver.save()

            event_serializer = RidingEventSerializer(riding_event)
            return Response({
                'message': 'Riding event created successfully',
                'event': event_serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': f'Failed to create riding event: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserRidingEventsView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RidingEventSerializer

    def get_queryset(self):
        user = self.request.user
        if user.account_type == 'user':
            return RidingEvent.objects.filter(user=user).order_by('-created_at')
        elif user.account_type == 'driver':
            return RidingEvent.objects.filter(driver=user).order_by('-created_at')
        return RidingEvent.objects.none()

class RidingEventDetailView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RidingEventSerializer
    queryset = RidingEvent.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.account_type == 'user':
            return RidingEvent.objects.filter(user=user)
        elif user.account_type == 'driver':
            return RidingEvent.objects.filter(driver=user)
        return RidingEvent.objects.none()
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if instance.payment_completed:
            allowed_fields = {'status'}
            if not set(request.data.keys()).issubset(allowed_fields):
                return Response({
                    'error': 'Cannot edit event details after payment is completed. Only status can be updated.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if request.user.account_type == 'user' and instance.user != request.user:
            return Response({
                'error': 'You do not have permission to edit this event'
            }, status=status.HTTP_403_FORBIDDEN)
        elif request.user.account_type == 'driver' and instance.driver != request.user:
            return Response({
                'error': 'You do not have permission to edit this event'
            }, status=status.HTTP_403_FORBIDDEN)
        
        old_status = instance.status
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        new_status = serializer.instance.status
        if old_status != new_status and new_status in ['completed', 'cancelled']:
            driver = instance.driver
            driver.driver_is_available = True
            driver.save()
        
        return Response({
            'message': 'Riding event updated successfully',
            'event': serializer.data
        }, status=status.HTTP_200_OK)

class CompletePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, event_id):
        try:
            event = RidingEvent.objects.get(id=event_id, user=request.user)
        except RidingEvent.DoesNotExist:
            return Response({
                'error': 'Riding event not found or you do not have permission'
            }, status=status.HTTP_404_NOT_FOUND)

        if event.payment_completed:
            return Response({
                'error': 'Payment already completed'
            }, status=status.HTTP_400_BAD_REQUEST)

        event.payment_completed = True
        event.save()

        return Response({
            'message': 'Payment completed successfully',
            'event': RidingEventSerializer(event).data
        }, status=status.HTTP_200_OK)