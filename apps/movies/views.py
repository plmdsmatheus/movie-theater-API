import uuid
from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework import generics, permissions, status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .tasks import send_ticket_confirmation_email_task

from apps.core.cache_keys import (
    build_movies_list_cache_key,
    build_movie_sessions_cache_key,
)

from .models import Movie, Session, Seat, SeatLock, Ticket
from .serializers import (
    MovieListSerializer,
    SessionListSerializer,
    SeatMapResponseSerializer,
    SeatReservationRequestSerializer,
    SeatReservationResponseSerializer,
    SeatReleaseResponseSerializer,
    SeatCheckoutRequestSerializer,
    SeatCheckoutResponseSerializer,
    TicketSerializer,
    MyTicketListSerializer,
)
from .services import SeatLockService
from apps.core.throttles import SeatReserveRateThrottle, SeatCheckoutRateThrottle

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

    def list(self, request, *args, **kwargs):
        """
        I cache paginated movie list responses in Redis to improve performance
        for high-read traffic.
        """
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 10)

        cache_key = build_movies_list_cache_key(
            page=page,
            page_size=page_size,
        )

        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return Response(cached_response)

        response = super().list(request, *args, **kwargs)

        cache.set(
            cache_key,
            response.data,
            timeout=settings.MOVIES_LIST_CACHE_TTL,
        )

        return response


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

    I return only:
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
        I filter sessions by:
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

    def list(self, request, *args, **kwargs):
        """
        I cache paginated session list responses in Redis because this endpoint
        is expected to be read frequently by users browsing movie sessions.
        """
        movie_id = self.kwargs["movie_id"]
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 10)

        cache_key = build_movie_sessions_cache_key(
            movie_id=movie_id,
            page=page,
            page_size=page_size,
        )

        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return Response(cached_response)

        response = super().list(request, *args, **kwargs)

        cache.set(
            cache_key,
            response.data,
            timeout=settings.MOVIE_SESSIONS_CACHE_TTL,
        )

        return response

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
    throttle_classes = [SeatReserveRateThrottle]

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

@extend_schema(
    tags=['Sessions'],
    summary='Checkout a reserved seat and generate a ticket',
    description=(
        'Converts a temporary Redis seat lock into a permanent ticket. '
        'The authenticated user must own the active lock for the selected seat.'
    ),
    request=SeatCheckoutRequestSerializer,
    responses={
        201: OpenApiResponse(
            response=SeatCheckoutResponseSerializer,
            description='Ticket generated successfully.'
        ),
        400: OpenApiResponse(description='Invalid request.'),
        401: OpenApiResponse(description='Authentication required.'),
        403: OpenApiResponse(description='The lock does not belong to the authenticated user.'),
        404: OpenApiResponse(description='Session, seat, or active lock not found.'),
        409: OpenApiResponse(description='Seat already purchased.')
    },
    examples=[
        OpenApiExample(
            'Checkout request',
            value={
                'seat_id': 12
            },
            request_only=True,
        ),
        OpenApiExample(
            'Checkout success response',
            value={
                'message': 'Ticket generated successfully.',
                'ticket': {
                    'id': 1,
                    'ticket_code': 'b7b8e0b2-4dd5-4b47-bf43-6c4f5f0ef111',
                    'status': 'ACTIVE',
                    'purchased_at': '2026-03-17T14:00:00-03:00',
                    'movie_title': 'Dune: Part Two',
                    'room_name': 'Room 1',
                    'seat_code': 'A2',
                    'session_start_time': '2026-03-18T19:00:00-03:00'
                }
            },
            response_only=True,
            status_codes=['201'],
        ),
    ],
)
class SessionSeatCheckoutView(APIView):
    """
    CASE 6:
    I convert a temporary seat lock into a permanent ticket.

    I require authentication because checkout is a user-owned action.
    I only allow checkout when the authenticated user owns the active Redis lock.
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [SeatReserveRateThrottle]

    def post(self, request, session_id):
        """
        I validate the request, confirm that the seat belongs to the session room,
        verify the active lock ownership, prevent duplicate purchases, create the
        ticket in the database, and finally release the Redis lock.
        """
        serializer = SeatCheckoutRequestSerializer(data=request.data)
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

        lock_data = SeatLockService.get_lock_data(
            session_id=session.id,
            seat_id=seat.id,
        )

        if not lock_data:
            return Response(
                {"detail": "No active seat lock was found for this seat."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if lock_data.get("user_id") != request.user.id:
            return Response(
                {"detail": "You cannot checkout a seat reserved by another user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        existing_ticket = Ticket.objects.filter(
            session=session,
            seat=seat,
            status__in=[Ticket.STATUS_ACTIVE, Ticket.STATUS_USED],
        ).first()

        if existing_ticket:
            return Response(
                {"detail": "This seat has already been purchased."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            with transaction.atomic():
                ticket = Ticket.objects.create(
                    user=request.user,
                    session=session,
                    seat=seat,
                    ticket_code=str(uuid.uuid4()),
                    status=Ticket.STATUS_ACTIVE,
                )
        except IntegrityError:
            return Response(
                {"detail": "This seat has already been purchased."},
                status=status.HTTP_409_CONFLICT,
            )

        SeatLockService.release_lock(
            session_id=session.id,
            seat_id=seat.id,
            user_id=request.user.id,
        )

        response_payload = {
            "message": "Ticket generated successfully.",
            "ticket": ticket,
        }

        send_ticket_confirmation_email_task.delay(
            user_email=request.user.email,
            movie_title=session.movie.title,
            room_name=session.room.name,
            seat_code=seat.seat_code,
            session_start_time=session.start_time.isoformat(),
            ticket_code=ticket.ticket_code,
        )

        response_serializer = SeatCheckoutResponseSerializer(response_payload)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

@extend_schema(
    tags=['Tickets'],
    summary='List tickets for the authenticated user',
    description=(
        'Returns tickets that belong to the authenticated user. '
        'The optional "type" query parameter can be used to filter results:\n'
        '- active: upcoming active tickets only\n'
        '- history: complete purchase history\n'
        '- omitted: all tickets'
    ),
    responses={
        200: OpenApiResponse(
            response=MyTicketListSerializer(many=True),
            description='Tickets returned successfully.'
        ),
        401: OpenApiResponse(description='Authentication required.')
    },
    examples=[
        OpenApiExample(
            'My tickets response',
            value=[
                {
                    'id': 1,
                    'ticket_code': '5f40cb67-c7cc-4c72-95c0-7fce7686f0c2',
                    'status': 'ACTIVE',
                    'purchased_at': '2026-03-17T15:00:00-03:00',
                    'movie_title': 'Dune: Part Two',
                    'room_name': 'Room 1',
                    'seat_code': 'A1',
                    'session_start_time': '2026-03-18T19:00:00-03:00',
                    'session_end_time': '2026-03-18T21:46:00-03:00',
                    'session_language': 'SUB',
                    'session_format': '2D',
                    'is_upcoming': True
                }
            ],
            response_only=True,
            status_codes=['200'],
        )
    ],
)
class MyTicketsListView(generics.ListAPIView):
    """
    CASE 7:
    I return tickets that belong to the authenticated user.

    I support two main modes:
    - active: upcoming tickets that are still active
    - history: complete ticket history

    If no filter is provided, I return all tickets for the authenticated user.
    """

    serializer_class = MyTicketListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        I filter tickets according to the authenticated user and the optional
        query parameter provided by the client.
        """
        ticket_type = self.request.query_params.get("type")

        queryset = (
            Ticket.objects.select_related("session", "session__movie", "session__room", "seat")
            .filter(user=self.request.user)
            .order_by("-purchased_at")
        )

        if ticket_type == "active":
            queryset = queryset.filter(
                status=Ticket.STATUS_ACTIVE,
                session__start_time__gt=timezone.now(),
            )

        elif ticket_type == "history":
            queryset = queryset

        return queryset