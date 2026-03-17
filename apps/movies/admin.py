from django.contrib import admin
from .models import Movie, Room, Session


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """
    Admin configuration for movies.
    """

    list_display = ('id', 'title', 'duration_minutes', 'rating', 'is_active', 'created_at')
    list_filter = ('is_active', 'rating')
    search_fields = ('title',)
    ordering = ('title',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """
    Admin configuration for rooms.
    """

    list_display = ('id', 'name', 'total_rows', 'total_columns', 'capacity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """
    Admin configuration for sessions.
    """

    list_display = (
        'id',
        'movie',
        'room',
        'start_time',
        'end_time',
        'language',
        'format_type',
        'is_active',
    )
    list_filter = ('is_active', 'language', 'format_type', 'room')
    search_fields = ('movie__title', 'room__name')
    ordering = ('start_time',)