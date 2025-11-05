import os
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import RidingEvent, StripePayment
from .serializers import CreatePaymentIntentSerializer, StripePaymentSerializer
from .stripe_utils import create_payment_intent, confirm_payment_intent, construct_webhook_event, confirm_payment_with_test_card


class CreatePaymentIntentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        riding_event_id = serializer.validated_data['riding_event_id']

        try:
            riding_event = RidingEvent.objects.get(id=riding_event_id)

            if riding_event.user != request.user:
                return Response({
                    'error': 'You do not have permission to create payment for this event'
                }, status=status.HTTP_403_FORBIDDEN)

            if hasattr(riding_event, 'stripe_payment'):
                stripe_payment = riding_event.stripe_payment
                if stripe_payment.status in ['succeeded']:
                    return Response({
                        'error': 'Payment already completed for this event',
                        'payment': StripePaymentSerializer(stripe_payment).data
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif stripe_payment.status == 'pending':
                    return Response({
                        'message': 'Payment intent already exists',
                        'client_secret': stripe_payment.stripe_payment_intent_id,
                        'payment_intent_id': stripe_payment.stripe_payment_intent_id,
                        'amount': float(riding_event.charge_amount),
                        'payment': StripePaymentSerializer(stripe_payment).data
                    }, status=status.HTTP_200_OK)
                else:
                    stripe_payment.delete()

            metadata = {
                'riding_event_id': str(riding_event.id),
                'user_id': str(request.user.id),
                'from_where': riding_event.from_where,
                'to_where': riding_event.to_where,
            }

            payment_intent = create_payment_intent(
                amount=float(riding_event.charge_amount),
                currency='usd',
                metadata=metadata
            )

            stripe_payment = StripePayment.objects.create(
                riding_event=riding_event,
                stripe_payment_intent_id=payment_intent.id,
                amount=riding_event.charge_amount,
                currency='usd',
                status='pending',
                customer_email=request.user.email
            )

            riding_event.stripe_payment_intent_id = payment_intent.id
            riding_event.save()

            return Response({
                'message': 'Payment intent created successfully',
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': float(riding_event.charge_amount),
                'payment': StripePaymentSerializer(stripe_payment).data
            }, status=status.HTTP_201_CREATED)

        except RidingEvent.DoesNotExist:
            return Response({
                'error': 'Riding event not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to create payment intent: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payment_intent_id = request.data.get('payment_intent_id')

        if not payment_intent_id:
            return Response({
                'error': 'payment_intent_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment_intent = confirm_payment_intent(payment_intent_id)

            stripe_payment = StripePayment.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )

            if stripe_payment.riding_event.user != request.user:
                return Response({
                    'error': 'You do not have permission to confirm this payment'
                }, status=status.HTTP_403_FORBIDDEN)

            if payment_intent.status == 'succeeded':
                stripe_payment.status = 'succeeded'
                stripe_payment.stripe_charge_id = payment_intent.charges.data[0].id if payment_intent.charges.data else None
                stripe_payment.save()

                riding_event = stripe_payment.riding_event
                riding_event.payment_completed = True
                riding_event.status = 'in_progress'
                riding_event.save()

                return Response({
                    'message': 'Payment confirmed successfully',
                    'status': payment_intent.status,
                    'payment': StripePaymentSerializer(stripe_payment).data
                }, status=status.HTTP_200_OK)
            
            elif payment_intent.status == 'requires_payment_method':
                stripe_payment.status = 'pending'
                stripe_payment.error_message = 'Awaiting payment method from client'
                stripe_payment.save()

                return Response({
                    'message': 'Payment method required. Please complete payment on the client side.',
                    'status': payment_intent.status,
                    'client_secret': payment_intent.client_secret,
                    'payment': StripePaymentSerializer(stripe_payment).data
                }, status=status.HTTP_200_OK)
            
            elif payment_intent.status == 'processing':
                stripe_payment.status = 'pending'
                stripe_payment.error_message = 'Payment is being processed'
                stripe_payment.save()

                return Response({
                    'message': 'Payment is being processed',
                    'status': payment_intent.status,
                    'payment': StripePaymentSerializer(stripe_payment).data
                }, status=status.HTTP_200_OK)
            
            elif payment_intent.status in ['requires_action', 'requires_confirmation']:
                stripe_payment.status = 'pending'
                stripe_payment.error_message = f'Payment requires action: {payment_intent.status}'
                stripe_payment.save()

                return Response({
                    'message': f'Payment requires additional action',
                    'status': payment_intent.status,
                    'client_secret': payment_intent.client_secret,
                    'next_action': payment_intent.next_action if hasattr(payment_intent, 'next_action') else None,
                    'payment': StripePaymentSerializer(stripe_payment).data
                }, status=status.HTTP_200_OK)
            
            else:
                stripe_payment.status = 'failed'
                stripe_payment.error_message = f"Payment status: {payment_intent.status}"
                if hasattr(payment_intent, 'last_payment_error') and payment_intent.last_payment_error:
                    stripe_payment.error_message = payment_intent.last_payment_error.message
                stripe_payment.save()

                return Response({
                    'message': 'Payment failed',
                    'status': payment_intent.status,
                    'error': stripe_payment.error_message,
                    'payment': StripePaymentSerializer(stripe_payment).data
                }, status=status.HTTP_400_BAD_REQUEST)

        except StripePayment.DoesNotExist:
            return Response({
                'error': 'Payment record not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to confirm payment: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        if not webhook_secret:
            return HttpResponse('Webhook secret not configured', status=500)

        if settings.DEBUG and not sig_header:
            try:
                import json
                event = json.loads(payload)
                class WebhookEvent:
                    def __init__(self, data):
                        self.type = data.get('type')
                        self.data = type('obj', (object,), {'object': data.get('data', {}).get('object', {})})()
                
                event = WebhookEvent(event)
            except Exception as e:
                return HttpResponse(f'Webhook error parsing payload: {str(e)}', status=400)
        else:
            try:
                event = construct_webhook_event(payload, sig_header, webhook_secret)
            except Exception as e:
                return HttpResponse(f'Webhook error: {str(e)}', status=400)

        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object
            self._handle_payment_succeeded(payment_intent)

        elif event.type == 'payment_intent.payment_failed':
            payment_intent = event.data.object
            self._handle_payment_failed(payment_intent)

        elif event.type == 'charge.refunded':
            charge = event.data.object
            self._handle_charge_refunded(charge)

        return HttpResponse('Success', status=200)

    def _handle_payment_succeeded(self, payment_intent):
        try:
            stripe_payment = StripePayment.objects.get(
                stripe_payment_intent_id=payment_intent.id
            )
            stripe_payment.status = 'succeeded'
            stripe_payment.stripe_charge_id = payment_intent.charges.data[0].id if payment_intent.charges.data else None
            stripe_payment.save()

            riding_event = stripe_payment.riding_event
            riding_event.payment_completed = True
            riding_event.status = 'in_progress'
            riding_event.save()

        except StripePayment.DoesNotExist:
            pass

    def _handle_payment_failed(self, payment_intent):
        try:
            stripe_payment = StripePayment.objects.get(
                stripe_payment_intent_id=payment_intent.id
            )
            stripe_payment.status = 'failed'
            stripe_payment.error_message = payment_intent.last_payment_error.message if payment_intent.last_payment_error else 'Payment failed'
            stripe_payment.save()

        except StripePayment.DoesNotExist:
            pass

    def _handle_charge_refunded(self, charge):
        try:
            stripe_payment = StripePayment.objects.get(
                stripe_charge_id=charge.id
            )
            stripe_payment.status = 'refunded'
            stripe_payment.save()

            riding_event = stripe_payment.riding_event
            riding_event.payment_completed = False
            riding_event.status = 'cancelled'
            riding_event.save()

        except StripePayment.DoesNotExist:
            pass


class TestPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not settings.DEBUG:
            return Response({
                'error': 'This endpoint is only available in DEBUG mode'
            }, status=status.HTTP_403_FORBIDDEN)

        payment_intent_id = request.data.get('payment_intent_id')

        if not payment_intent_id:
            return Response({
                'error': 'payment_intent_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            stripe_payment = StripePayment.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )

            if stripe_payment.riding_event.user != request.user:
                return Response({
                    'error': 'You do not have permission to test this payment'
                }, status=status.HTTP_403_FORBIDDEN)

            payment_intent = confirm_payment_with_test_card(payment_intent_id)

            if payment_intent.status == 'succeeded':
                stripe_payment.status = 'succeeded'
                
                if hasattr(payment_intent, 'charges') and payment_intent.charges and hasattr(payment_intent.charges, 'data'):
                    if len(payment_intent.charges.data) > 0:
                        stripe_payment.stripe_charge_id = payment_intent.charges.data[0].id
                elif hasattr(payment_intent, 'latest_charge') and payment_intent.latest_charge:
                    stripe_payment.stripe_charge_id = payment_intent.latest_charge
                
                stripe_payment.save()

                riding_event = stripe_payment.riding_event
                riding_event.payment_completed = True
                riding_event.status = 'in_progress'
                riding_event.save()

                return Response({
                    'message': 'Test payment completed successfully',
                    'status': payment_intent.status,
                    'payment': StripePaymentSerializer(stripe_payment).data,
                    'riding_event': {
                        'id': riding_event.id,
                        'status': riding_event.status,
                        'payment_completed': riding_event.payment_completed
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'Payment processing',
                    'status': payment_intent.status,
                    'payment': StripePaymentSerializer(stripe_payment).data
                }, status=status.HTTP_200_OK)

        except StripePayment.DoesNotExist:
            return Response({
                'error': 'Payment record not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            error_details = {
                'error': f'Failed to complete test payment: {str(e)}',
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }
            return Response(error_details, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
