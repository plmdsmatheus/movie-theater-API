from django.urls import path
from .views import MovieListView, MovieSessionListView

urlpatterns = [
    path('movies/', MovieListView.as_view(), name='movie-list'),
    path('movies/<int:movie_id>/sessions/', MovieSessionListView.as_view(), name='movie-sessions'),
]