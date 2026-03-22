from django.urls import path
from .views import (
    MovieListView,
    MovieSessionListView,
    SessionSeatMapView,
    SessionSeatReserveView,
    SessionSeatReleaseView,
    SessionSeatCheckoutView,
    MyTicketsListView,
)

# URL patterns for movie browsing and ticket reservation system.
# These endpoints handle movie listing, session discovery, seat management,
# and ticket purchasing workflow.

urlpatterns = [
    # Endpoint to list all available movies.
    # Typically used by clients to display the movie catalog.
    path('movies/', MovieListView.as_view(), name='movie-list'),

    # Endpoint to list all sessions (showtimes) for a specific movie.
    # Requires a movie_id to filter sessions.
    path('movies/<int:movie_id>/sessions/', MovieSessionListView.as_view(), name='movie-sessions'),

    # Endpoint to retrieve the seat map for a specific session.
    # Returns seat availability and current reservation status.
    path('sessions/<int:session_id>/seat-map/', SessionSeatMapView.as_view(), name='session-seat-map'),

    # Endpoint to reserve a specific seat for a session.
    # Usually locks the seat temporarily for the authenticated user.
    path('sessions/<int:session_id>/reserve-seat/', SessionSeatReserveView.as_view(), name='session-seat-reserve'),

    # Endpoint to release a previously reserved seat.
    # Makes the seat available again for other users.
    path('sessions/<int:session_id>/release-seat/', SessionSeatReleaseView.as_view(), name='session-seat-release'),

    # Endpoint to finalize the purchase (checkout) of reserved seats.
    # Converts reservations into confirmed tickets.
    path('sessions/<int:session_id>/checkout/', SessionSeatCheckoutView.as_view(), name='session-seat-checkout'),

    # Endpoint to list all tickets purchased by the authenticated user.
    # Useful for user history and ticket management.
    path('my-tickets/', MyTicketsListView.as_view(), name='my-tickets'),
]