from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<riding_event_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/drivers/$', consumers.DriverLocationConsumer.as_asgi()),
]
