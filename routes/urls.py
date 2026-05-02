from django.urls import path
from . import views

urlpatterns = [
    path('destinations/', views.get_destinations, name='destinations'),
]