from django.utils import timezone
from rest_framework import serializers
from .models import Movie, Room, Session, Seat, SeatLock, Ticket


class MovieListSerializer(serializers.ModelSerializer):
    """
    I use this serializer to list movies in CASE 2.
    """

    class Meta:
        model = Movie
        fields = [
            'id',
            'title',
            'description',
            'duration_minutes',
            'rating',
            'poster_url',
            'is_active',
        ]


class RoomSerializer(serializers.ModelSerializer):
    """
    I use this serializer to expose room data inside session responses.
    """

    capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Room
        fields = [
            'id',
            'name',
            'total_rows',
            'total_columns',
            'capacity',
        ]


class SessionListSerializer(serializers.ModelSerializer):
    """
    I use this serializer to list sessions for a specific movie in CASE 3.
    """

    room = RoomSerializer(read_only=True)
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)

    class Meta:
        model = Session
        fields = [
            'id',
            'movie',
            'movie_title',
            'room',
            'start_time',
            'end_time',
            'language',
            'format_type',
            'is_active',
            'is_upcoming',
        ]


class SeatMapSeatSerializer(serializers.Serializer):
    """
    I use this serializer to represent one seat in the seat map response.
    """

    seat_id = serializers.IntegerField()
    seat_code = serializers.CharField()
    row = serializers.CharField()
    number = serializers.IntegerField()
    status = serializers.CharField()


class SeatMapResponseSerializer(serializers.Serializer):
    """
    I use this serializer to document the seat map endpoint response.
    """

    session_id = serializers.IntegerField()
    movie = serializers.CharField()
    room = serializers.CharField()
    start_time = serializers.DateTimeField()
    seat_map = serializers.ListField(
        child=serializers.ListField(
            child=SeatMapSeatSerializer()
        )
    )

class SeatReservationRequestSerializer(serializers.Serializer):
    """
    I use this serializer to validate seat reservation requests.
    """

    seat_id = serializers.IntegerField()


class SeatReservationResponseSerializer(serializers.Serializer):
    """
    I use this serializer to document successful seat reservation responses.
    """

    message = serializers.CharField()
    session_id = serializers.IntegerField()
    seat_id = serializers.IntegerField()
    status = serializers.CharField()
    expires_in_seconds = serializers.IntegerField()

class SeatReleaseResponseSerializer(serializers.Serializer):
    """
    I use this serializer to document seat lock release responses.
    """

    message = serializers.CharField()
    session_id = serializers.IntegerField()
    seat_id = serializers.IntegerField()
    status = serializers.CharField()

class SeatCheckoutRequestSerializer(serializers.Serializer):
    """
    I use this serializer to validate checkout requests.
    """

    seat_id = serializers.IntegerField()


class TicketSerializer(serializers.ModelSerializer):
    """
    I use this serializer to expose ticket data after checkout.
    """

    movie_title = serializers.CharField(source='session.movie.title', read_only=True)
    room_name = serializers.CharField(source='session.room.name', read_only=True)
    seat_code = serializers.CharField(source='seat.seat_code', read_only=True)
    session_start_time = serializers.DateTimeField(source='session.start_time', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'ticket_code',
            'status',
            'purchased_at',
            'movie_title',
            'room_name',
            'seat_code',
            'session_start_time',
        ]


class SeatCheckoutResponseSerializer(serializers.Serializer):
    """
    I use this serializer to document successful checkout responses.
    """

    message = serializers.CharField()
    ticket = TicketSerializer()