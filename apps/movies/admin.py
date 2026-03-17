from django.contrib import admin
from .models import Movie, Room, Seat, Session, SeatLock, Ticket


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """
    I configure how movies appear in Django admin.
    """

    list_display = ('id', 'title', 'duration_minutes', 'rating', 'is_active', 'created_at')
    list_filter = ('is_active', 'rating')
    search_fields = ('title',)
    ordering = ('title',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """
    I configure how rooms appear in Django admin.
    """

    list_display = ('id', 'name', 'total_rows', 'total_columns', 'capacity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    """
    I configure how seats appear in Django admin.
    """

    list_display = ('id', 'room', 'row_label', 'number', 'seat_code')
    list_filter = ('room',)
    search_fields = ('seat_code', 'room__name')
    ordering = ('room', 'row_label', 'number')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """
    I configure how sessions appear in Django admin.
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


@admin.register(SeatLock)
class SeatLockAdmin(admin.ModelAdmin):
    """
    I configure how seat locks appear in Django admin.
    """

    list_display = ('id', 'session', 'seat', 'user', 'status', 'locked_at', 'expires_at')
    list_filter = ('status', 'session')
    search_fields = ('seat__seat_code', 'user__username', 'session__movie__title')
    ordering = ('-locked_at',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    I configure how tickets appear in Django admin.
    """

    list_display = ('id', 'ticket_code', 'user', 'session', 'seat', 'status', 'purchased_at')
    list_filter = ('status', 'session')
    search_fields = ('ticket_code', 'user__username', 'seat__seat_code', 'session__movie__title')
    ordering = ('-purchased_at',)