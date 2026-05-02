from django.urls import path
from . import views

urlpatterns = [
    path('destinations/', views.get_destinations, name='destinations'),
    path('cities/', views.get_cities, name='cities'),

    path('trips/', views.trips_manager, name='trips-manager'),
    path('trips/<slug:slug>/', views.trip_detail, name='trip-detail'),
    path('trips/<slug:slug>/connections/', views.get_trip_connections, name='trip-connections-list'),

    path('connections/', views.add_connection, name='add_connection'),
    path('connections/<int:pk>/', views.connection_detail, name='connection-detail'),
]