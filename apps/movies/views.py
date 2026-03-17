from django.utils import timezone
from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse

from .models import Movie, Session
from .serializers import MovieListSerializer, SessionListSerializer


@extend_schema(
    tags=['Movies'],
    summary='List all available movies',
    description=(
        'Returns all active movies currently available in the catalog. '
        'Only movies marked as active are returned.'
    ),
    responses={
        200: OpenApiResponse(
            response=MovieListSerializer(many=True),
            description='List of available movies returned successfully.'
        )
    },
    examples=[
        OpenApiExample(
            'Movies list response',
            value=[
                {
                    'id': 1,
                    'title': 'Dune: Part Two',
                    'description': 'Paul Atreides unites with Chani and the Fremen...',
                    'duration_minutes': 166,
                    'rating': '14',
                    'poster_url': 'https://example.com/posters/dune2.jpg',
                    'is_active': True
                },
                {
                    'id': 2,
                    'title': 'Inside Out 2',
                    'description': 'Teen Riley encounters new emotions...',
                    'duration_minutes': 96,
                    'rating': 'L',
                    'poster_url': 'https://example.com/posters/insideout2.jpg',
                    'is_active': True
                }
            ],
            response_only=True,
            status_codes=['200'],
        )
    ],
)
class MovieListView(generics.ListAPIView):
    """
    CASE 2:
    List all available movies.

    I made this endpoint public because the business requirement states that
    both authenticated and non-authenticated users should be able to view
    the movie catalog.
    """

    serializer_class = MovieListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        I return only active movies.

        I keep this method explicit to make future filtering easier,
        such as:
        - filtering by title
        - filtering by rating
        - filtering by genre
        """
        return Movie.objects.filter(is_active=True).order_by('title')


@extend_schema(
    tags=['Movies'],
    summary='List available sessions for a specific movie',
    description=(
        'Returns all active and upcoming sessions for a specific movie. '
        'The movie is identified by its ID in the URL.'
    ),
    parameters=[
        OpenApiParameter(
            name='movie_id',
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
            description='ID of the movie whose sessions should be listed.'
        )
    ],
    responses={
        200: OpenApiResponse(
            response=SessionListSerializer(many=True),
            description='List of sessions returned successfully.'
        )
    },
    examples=[
        OpenApiExample(
            'Sessions list response',
            value=[
                {
                    'id': 10,
                    'movie': 1,
                    'movie_title': 'Dune: Part Two',
                    'room': {
                        'id': 1,
                        'name': 'Room 1',
                        'total_rows': 10,
                        'total_columns': 12,
                        'capacity': 120
                    },
                    'start_time': '2026-03-18T19:00:00-03:00',
                    'end_time': '2026-03-18T21:46:00-03:00',
                    'language': 'SUB',
                    'format_type': '2D',
                    'is_active': True,
                    'is_upcoming': True
                }
            ],
            response_only=True,
            status_codes=['200'],
        )
    ],
)
class MovieSessionListView(generics.ListAPIView):
    """
    CASE 3:
    List all available sessions for a specific movie.

    Return only:
    - sessions linked to the requested movie
    - sessions marked as active
    - sessions that have not started yet

    I designed this behavior to ensure that only valid and available sessions
    are exposed to users.

    This endpoint is public because both authenticated and non-authenticated
    users should be able to browse sessions.
    """

    serializer_class = SessionListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Filters sessions by:
        1. movie ID from the URL
        2. active sessions only
        3. upcoming sessions only

        I use select_related to optimize database queries by joining
        movie and room in a single query.
        """
        movie_id = self.kwargs['movie_id']

        return (
            Session.objects.select_related('movie', 'room')
            .filter(
                movie_id=movie_id,
                is_active=True,
                movie__is_active=True,
                start_time__gt=timezone.now()
            )
            .order_by('start_time')
        )