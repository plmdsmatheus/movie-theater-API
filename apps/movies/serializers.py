from rest_framework import serializers
from .models import Movie, Room, Session


class MovieListSerializer(serializers.ModelSerializer):
    """
    Serializer used to list movies in CASE 2.
    Keeps the response clean and focused on catalog information.
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
    Serializer for room data.
    Used as nested data inside session responses.
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
    Serializer used to list sessions for a specific movie in CASE 3.
    Includes nested room information and useful computed fields.
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