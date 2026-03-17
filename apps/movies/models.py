from django.db import models
from django.utils import timezone


class Movie(models.Model):
    """
    Represents a movie available in the theater catalog.
    This model is used in CASE 2 to list all available movies.
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
    Each session happens inside one room.
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
        Calculates the total seat capacity for the room.
        This will be useful later when implementing seat maps.
        """
        return self.total_rows * self.total_columns


class Session(models.Model):
    """
    Represents a movie session/showtime.
    This model is used in CASE 3 to list available sessions for a specific movie.
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
        Returns True if the session is still in the future.
        """
        return self.start_time > timezone.now()

    def clean(self):
        """
        Optional validation hook.
        Ensures the session end time is later than the start time.
        """
        from django.core.exceptions import ValidationError

        if self.end_time <= self.start_time:
            raise ValidationError('End time must be greater than start time.')