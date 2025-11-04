from django.urls import path
from .views import (
    CreateRidingEventView,
    UserRidingEventsView,
    RidingEventDetailView,
    CompletePaymentView,
)

urlpatterns = [
    path('create-event/', CreateRidingEventView.as_view(), name='create-riding-event'),
    path('my-events/', UserRidingEventsView.as_view(), name='user-riding-events'),
    path('event/<int:pk>/', RidingEventDetailView.as_view(), name='riding-event-detail'),
    path('event/<int:event_id>/complete-payment/', CompletePaymentView.as_view(), name='complete-payment'),
]