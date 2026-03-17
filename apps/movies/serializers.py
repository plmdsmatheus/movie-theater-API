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