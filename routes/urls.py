from django.urls import path
from . import views

urlpatterns = [
    path('destinations/', views.get_destinations, name='destinations'),
    path('cities/', views.get_cities, name='cities'),
    path('trips/', views.create_trip, name='create_trip'),
]