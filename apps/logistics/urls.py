from django.urls import path

from apps.logistics.api import views

urlpatterns = [
    path('destinations/', views.get_destinations, name='destinations'),
    path('destinations/stop/', views.get_destinations_from_stop, name='destinations-from-stop'),
    path('cities/', views.get_cities, name='cities'),
    path('cities/<str:city_id>/', views.get_city_detail, name='city-detail'),
    path('stops/', views.get_stops, name='stops'),
]
