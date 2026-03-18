from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Movie(models.Model):
    """
    Represents a movie available in the theater catalog.
    I use this model to expose the movie catalog in CASE 2.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    rating = models.CharField(
        max_length=10,
        blank=True,
        help_text="Movie age rating, e.g. G, PG-13, 14, 18"
    )
    poster_url = models.URLField(blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Defines whether the movie is currently available in the catalog."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Movie'
        verbose_name_plural = 'Movies'

    def __str__(self):
        return self.title


class Room(models.Model):
    """
    Represents a theater room/auditorium.
    I use this model as the physical space where sessions happen.
    """

    name = models.CharField(max_length=100, unique=True)
    total_rows = models.PositiveIntegerField(default=10)
    total_columns = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'

    def __str__(self):
        return self.name

    @property
    def capacity(self):
        """
        I calculate the total room capacity from rows and columns.
        """
        return self.total_rows * self.total_columns


class Seat(models.Model):
    """
    Represents a physical seat inside a room.

    I model seats separately because the same room can host many sessions,
    while the seat structure itself remains the same.
    """

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='seats'
    )
    row_label = models.CharField(max_length=5)
    number = models.PositiveIntegerField()
    seat_code = models.CharField(max_length=10)

    class Meta:
        ordering = ['room', 'row_label', 'number']
        verbose_name = 'Seat'
        verbose_name_plural = 'Seats'
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'row_label', 'number'],
                name='unique_seat_per_room_position'
            ),
            models.UniqueConstraint(
                fields=['room', 'seat_code'],
                name='unique_seat_code_per_room'
            ),
        ]

    def __str__(self):
        return f'{self.room.name} - {self.seat_code}'

    def save(self, *args, **kwargs):
        """
        I automatically normalize seat_code before saving.

        Example:
        row_label='A' and number=1 => seat_code='A1'
        """
        self.row_label = self.row_label.upper().strip()
        self.seat_code = f'{self.row_label}{self.number}'
        super().save(*args, **kwargs)


class Session(models.Model):
    """
    Represents a movie session/showtime.
    I use this model to list sessions in CASE 3 and to group seat availability in CASE 4.
    """

    FORMAT_CHOICES = [
        ('2D', '2D'),
        ('3D', '3D'),
        ('IMAX', 'IMAX'),
    ]

    LANGUAGE_CHOICES = [
        ('SUB', 'Subtitled'),
        ('DUB', 'Dubbed'),
    ]

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='sessions'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='SUB')
    format_type = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='2D')
    is_active = models.BooleanField(
        default=True,
        help_text="Defines whether this session can still be listed or sold."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'

    def __str__(self):
        return f'{self.movie.title} - {self.start_time:%Y-%m-%d %H:%M}'

    @property
    def is_upcoming(self):
        """
        I return True when the session is still in the future.
        """
        return self.start_time > timezone.now()

    def clean(self):
        """
        I validate that the session end time is later than the start time.
        """
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be greater than start time.')


class SeatLock(models.Model):
    """
    Represents a temporary reservation for a seat in a specific session.

    I use this model to support the temporary locking behavior required by CASE 5,
    but I already introduce it now because CASE 4 needs to show RESERVED seats.
    """

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_EXPIRED = 'EXPIRED'
    STATUS_CONVERTED = 'CONVERTED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_CONVERTED, 'Converted'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='seat_locks'
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name='seat_locks'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seat_locks'
    )
    locked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )

    class Meta:
        ordering = ['expires_at']
        verbose_name = 'Seat Lock'
        verbose_name_plural = 'Seat Locks'

    def __str__(self):
        return f'{self.session} - {self.seat.seat_code} - {self.status}'

    @property
    def is_expired(self):
        """
        I check if the lock is already expired based on the current time.
        """
        return timezone.now() >= self.expires_at

    @property
    def is_active_lock(self):
        """
        I consider a lock active only when:
        - its status is ACTIVE
        - and its expiration time is still in the future
        """
        return self.status == self.STATUS_ACTIVE and not self.is_expired

    def clean(self):
        """
        I validate that the seat belongs to the same room as the session.
        """
        if self.seat.room_id != self.session.room_id:
            raise ValidationError('The seat must belong to the same room as the session.')

    @classmethod
    def default_expiration(cls):
        """
        I centralize the default lock duration here to make future changes easier.
        """
        return timezone.now() + timedelta(minutes=10)


class Ticket(models.Model):
    """
    Represents a purchased ticket for a seat in a session.

    I use this model to mark seats as PURCHASED and to support CASE 6 and CASE 7.
    """

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_USED = 'USED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_USED, 'Used'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    ticket_code = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-purchased_at']
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'seat'],
                condition=models.Q(status__in=['ACTIVE', 'USED']),
                name='unique_active_ticket_per_session_seat'
            )
        ]

    def __str__(self):
        return f'{self.ticket_code} - {self.session} - {self.seat.seat_code}'

    def clean(self):
        """
        I validate that the seat belongs to the same room as the session.
        """
        if self.seat.room_id != self.session.room_id:
            raise ValidationError('The seat must belong to the same room as the session.')