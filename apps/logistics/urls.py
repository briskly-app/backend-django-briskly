from django.urls import path

from apps.logistics.api import views

urlpatterns = [
    path('destinations/', views.get_destinations, name='destinations'),
    path('cities/', views.get_cities, name='cities'),
]
