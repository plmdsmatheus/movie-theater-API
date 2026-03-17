from django.utils import timezone
from rest_framework import generics, permissions, status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Movie, Session, Seat, SeatLock, Ticket
from .serializers import (
    MovieListSerializer,
    SessionListSerializer,
    SeatMapResponseSerializer,
    SeatReservationRequestSerializer,
    SeatReservationResponseSerializer,
    SeatReleaseResponseSerializer,
)
from .services import SeatLockService

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

@extend_schema(
    tags=['Sessions'],
    summary='Get seat map for a movie session',
    description=(
        'Returns the seat map for a specific session. '
        'Each seat is marked as AVAILABLE, RESERVED, or PURCHASED.'
    ),
    parameters=[
        OpenApiParameter(
            name='session_id',
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
            description='ID of the session whose seat map should be returned.'
        )
    ],
    responses={
        200: OpenApiResponse(
            response=SeatMapResponseSerializer,
            description='Seat map returned successfully.'
        ),
        404: OpenApiResponse(description='Session not found.')
    },
    examples=[
        OpenApiExample(
            'Seat map response',
            value={
                'session_id': 1,
                'movie': 'Dune: Part Two',
                'room': 'Room 1',
                'start_time': '2026-03-18T19:00:00-03:00',
                'seat_map': [
                    [
                        {
                            'seat_id': 1,
                            'seat_code': 'A1',
                            'row': 'A',
                            'number': 1,
                            'status': 'AVAILABLE'
                        },
                        {
                            'seat_id': 2,
                            'seat_code': 'A2',
                            'row': 'A',
                            'number': 2,
                            'status': 'RESERVED'
                        }
                    ],
                    [
                        {
                            'seat_id': 11,
                            'seat_code': 'B1',
                            'row': 'B',
                            'number': 1,
                            'status': 'PURCHASED'
                        }
                    ]
                ]
            },
            response_only=True,
            status_codes=['200'],
        )
    ],
)
class SessionSeatMapView(APIView):
    """
    CASE 4:
    Return the seat map for a specific movie session.

    Classify each seat using the following priority:
    1. PURCHASED
    2. RESERVED
    3. AVAILABLE

    I use this priority because a purchased seat should always take precedence
    over any temporary lock information.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, session_id):
        """
        I build the full seat map for the session's room and annotate each seat
        with its current status for that specific session.
        """
        session = get_object_or_404(
            Session.objects.select_related('movie', 'room'),
            id=session_id,
            is_active=True,
            movie__is_active=True,
        )

        room_seats = session.room.seats.all().order_by('row_label', 'number')

        purchased_seat_ids = set(
            Ticket.objects.filter(
                session=session,
                status__in=[Ticket.STATUS_ACTIVE, Ticket.STATUS_USED]
            ).values_list('seat_id', flat=True)
        )

        reserved_seat_ids = SeatLockService.list_reserved_seat_ids_for_session(session_id=session.id)

        grouped_rows = {}
        for seat in room_seats:
            if seat.id in purchased_seat_ids:
                status = 'PURCHASED'
            elif seat.id in reserved_seat_ids:
                status = 'RESERVED'
            else:
                status = 'AVAILABLE'

            grouped_rows.setdefault(seat.row_label, []).append({
                'seat_id': seat.id,
                'seat_code': seat.seat_code,
                'row': seat.row_label,
                'number': seat.number,
                'status': status,
            })

        seat_map = list(grouped_rows.values())

        payload = {
            'session_id': session.id,
            'movie': session.movie.title,
            'room': session.room.name,
            'start_time': session.start_time,
            'seat_map': seat_map,
        }

        serializer = SeatMapResponseSerializer(payload)
        return Response(serializer.data)
    
@extend_schema(
    tags=['Sessions'],
    summary='Reserve a seat temporarily for a movie session',
    description=(
        'Creates a temporary Redis lock for a seat in a specific session. '
        'The lock expires automatically after 10 minutes.'
    ),
    request=SeatReservationRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=SeatReservationResponseSerializer,
            description='Seat reserved successfully.'
        ),
        400: OpenApiResponse(description='Invalid request or seat does not belong to the session room.'),
        401: OpenApiResponse(description='Authentication required.'),
        409: OpenApiResponse(description='Seat already reserved or purchased.'),
        404: OpenApiResponse(description='Session or seat not found.')
    },
    examples=[
        OpenApiExample(
            'Reservation request',
            value={
                'seat_id': 12
            },
            request_only=True,
        ),
        OpenApiExample(
            'Reservation success response',
            value={
                'message': 'Seat reserved successfully.',
                'session_id': 1,
                'seat_id': 12,
                'status': 'RESERVED',
                'expires_in_seconds': 600
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
class SessionSeatReserveView(APIView):
    """
    CASE 5:
    I create a temporary Redis lock for a seat in a session.

    I require authentication because seat reservation is a user-owned action.
    A public user may browse movies and sessions, but only an authenticated
    user can reserve a seat.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        """
        I validate the request, confirm the seat belongs to the session room,
        ensure the seat was not purchased yet, and then try to lock it in Redis.
        """
        serializer = SeatReservationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        seat_id = serializer.validated_data["seat_id"]

        session = get_object_or_404(
            Session.objects.select_related("room", "movie"),
            id=session_id,
            is_active=True,
            movie__is_active=True,
            start_time__gt=timezone.now(),
        )

        seat = get_object_or_404(
            Seat,
            id=seat_id,
            room=session.room,
        )

        purchased_exists = Ticket.objects.filter(
            session=session,
            seat=seat,
            status__in=[Ticket.STATUS_ACTIVE, Ticket.STATUS_USED],
        ).exists()

        if purchased_exists:
            return Response(
                {"detail": "This seat has already been purchased."},
                status=status.HTTP_409_CONFLICT,
            )

        acquired = SeatLockService.acquire_lock(
            session_id=session.id,
            seat_id=seat.id,
            user_id=request.user.id,
        )

        if not acquired:
            lock_data = SeatLockService.get_lock_data(
                session_id=session.id,
                seat_id=seat.id,
            )
            ttl = SeatLockService.get_lock_ttl(
                session_id=session.id,
                seat_id=seat.id,
            )

            return Response(
                {
                    "detail": "This seat is currently reserved.",
                    "locked_by_user_id": lock_data.get("user_id") if lock_data else None,
                    "expires_in_seconds": ttl if ttl > 0 else 0,
                },
                status=status.HTTP_409_CONFLICT,
            )

        ttl = SeatLockService.get_lock_ttl(
            session_id=session.id,
            seat_id=seat.id,
        )

        response_payload = {
            "message": "Seat reserved successfully.",
            "session_id": session.id,
            "seat_id": seat.id,
            "status": "RESERVED",
            "expires_in_seconds": ttl if ttl > 0 else 0,
        }

        response_serializer = SeatReservationResponseSerializer(response_payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
@extend_schema(
    tags=['Sessions'],
    summary='Release a reserved seat lock',
    description='Releases a Redis seat lock owned by the authenticated user.',
    request=SeatReservationRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=SeatReleaseResponseSerializer,
            description='Seat lock released successfully.'
        ),
        400: OpenApiResponse(description='Invalid request.'),
        401: OpenApiResponse(description='Authentication required.'),
        403: OpenApiResponse(description='The lock does not belong to the authenticated user.'),
        404: OpenApiResponse(description='Lock not found.')
    },
)
class SessionSeatReleaseView(APIView):
    """
    I allow the authenticated user to release their own temporary seat lock.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        serializer = SeatReservationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        seat_id = serializer.validated_data["seat_id"]

        lock_data = SeatLockService.get_lock_data(session_id=session_id, seat_id=seat_id)
        if not lock_data:
            return Response(
                {"detail": "No active lock was found for this seat."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if lock_data.get("user_id") != request.user.id:
            return Response(
                {"detail": "You cannot release a lock owned by another user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        released = SeatLockService.release_lock(
            session_id=session_id,
            seat_id=seat_id,
            user_id=request.user.id,
        )

        if not released:
            return Response(
                {"detail": "Unable to release the seat lock."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_payload = {
            "message": "Seat lock released successfully.",
            "session_id": session_id,
            "seat_id": seat_id,
            "status": "AVAILABLE",
        }

        response_serializer = SeatReleaseResponseSerializer(response_payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)