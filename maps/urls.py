from django.urls import path
from .views import (
    CreateRidingEventView,
    UserRidingEventsView,
    RidingEventDetailView,
    CompletePaymentView,
)
from .stripe_views import (
    CreatePaymentIntentView,
    ConfirmPaymentView,
    StripeWebhookView,
    TestPaymentView,
)

urlpatterns = [
    path('create-event/', CreateRidingEventView.as_view(), name='create-riding-event'),
    path('my-events/', UserRidingEventsView.as_view(), name='user-riding-events'),
    path('event/<int:pk>/', RidingEventDetailView.as_view(), name='riding-event-detail'),
    path('event/<int:event_id>/complete-payment/', CompletePaymentView.as_view(), name='complete-payment'),
    path('create-payment-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('confirm-payment/', ConfirmPaymentView.as_view(), name='confirm-payment'),
    path('test-payment/', TestPaymentView.as_view(), name='test-payment'),
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
