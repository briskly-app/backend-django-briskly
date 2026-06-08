from django.urls import path

from apps.trips.api import views
from apps.trips.api.notes import views as note_views

urlpatterns = [
    path('trips/', views.trips_manager, name='trips-manager'),
    path('trips/<slug:slug>/', views.trip_detail, name='trip-detail'),
    path('trips/<slug:slug>/finalize/', views.trip_finalize, name='trip-finalize'),
    path('trips/<slug:slug>/journal/pdf/', views.trip_journal_pdf, name='trip-journal-pdf'),
    path('trips/<slug:slug>/connections/', views.get_trip_connections, name='trip-connections-list'),
    path('connections/', views.add_connection, name='add_connection'),
    path('connections/<int:id>/', views.connection_detail, name='connection-detail'),
    path(
        'connections/<int:connection_id>/notes/',
        note_views.connection_notes,
        name='connection-notes',
    ),
    path(
        'connections/<int:connection_id>/notes/reorder/',
        note_views.connection_notes_reorder,
        name='connection-notes-reorder',
    ),
    path(
        'connections/<int:connection_id>/notes/<int:note_id>/',
        note_views.connection_note_detail,
        name='connection-note-detail',
    ),
    path('notes/<int:id>/', note_views.note_detail, name='note-detail'),
]
