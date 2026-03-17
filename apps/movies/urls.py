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

urlpatterns = [
    path('movies/', MovieListView.as_view(), name='movie-list'),
    path('movies/<int:movie_id>/sessions/', MovieSessionListView.as_view(), name='movie-sessions'),
    path('sessions/<int:session_id>/seat-map/', SessionSeatMapView.as_view(), name='session-seat-map'),
    path('sessions/<int:session_id>/reserve-seat/', SessionSeatReserveView.as_view(), name='session-seat-reserve'),
    path('sessions/<int:session_id>/release-seat/', SessionSeatReleaseView.as_view(), name='session-seat-release'),
    path('sessions/<int:session_id>/checkout/', SessionSeatCheckoutView.as_view(), name='session-seat-checkout'),
    path('my-tickets/', MyTicketsListView.as_view(), name='my-tickets'),
]