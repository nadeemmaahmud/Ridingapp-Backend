from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, DriverLocationViewSet

router = DefaultRouter()
router.register(r'rooms', ChatRoomViewSet, basename='chatroom')
router.register(r'drivers', DriverLocationViewSet, basename='driverlocation')

urlpatterns = [
    path('', include(router.urls)),
]
