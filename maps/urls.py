from django.urls import path

from .views import map_view

urlpatterns = [
    path('geocode/', map_view, name='map-view'),
]