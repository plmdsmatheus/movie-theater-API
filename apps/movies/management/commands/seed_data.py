import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.movies.models import Movie, Room, Seat, Session, Ticket
from apps.movies.services import SeatLockService


class Command(BaseCommand):
    help = "Populate the database with sample data for local testing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting database seeding..."))

        # ---------------------------------------------------------------------
        # Create users
        # ---------------------------------------------------------------------
        users_data = [
            {
                "username": "matheus",
                "email": "matheus@email.com",
                "password": "12345678",
            },
            {
                "username": "ana",
                "email": "ana@email.com",
                "password": "12345678",
            },
            {
                "username": "carlos",
                "email": "carlos@email.com",
                "password": "12345678",
            },
        ]

        users = {}
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data["username"],
                defaults={"email": user_data["email"]},
            )

            # I reset the password every time so the seed remains predictable.
            user.email = user_data["email"]
            user.set_password(user_data["password"])
            user.save()

            users[user.username] = user

            if created:
                self.stdout.write(self.style.SUCCESS(f"User created: {user.username}"))
            else:
                self.stdout.write(f"User already existed and was updated: {user.username}")

        # ---------------------------------------------------------------------
        # Create movies
        # ---------------------------------------------------------------------
        movies_data = [
            {
                "title": "Dune: Part Two",
                "description": "Paul Atreides unites with Chani and the Fremen.",
                "duration_minutes": 166,
                "rating": "14",
                "poster_url": "https://example.com/posters/dune2.jpg",
                "is_active": True,
            },
            {
                "title": "Inside Out 2",
                "description": "Teen Riley faces new emotions.",
                "duration_minutes": 96,
                "rating": "L",
                "poster_url": "https://example.com/posters/insideout2.jpg",
                "is_active": True,
            },
            {
                "title": "The Batman",
                "description": "Batman uncovers corruption in Gotham City.",
                "duration_minutes": 176,
                "rating": "16",
                "poster_url": "https://example.com/posters/thebatman.jpg",
                "is_active": True,
            },
            {
                "title": "Old Archived Movie",
                "description": "Inactive movie for testing filters.",
                "duration_minutes": 120,
                "rating": "14",
                "poster_url": "https://example.com/posters/archived.jpg",
                "is_active": False,
            },
        ]

        movies = {}
        for movie_data in movies_data:
            movie, created = Movie.objects.update_or_create(
                title=movie_data["title"],
                defaults=movie_data,
            )
            movies[movie.title] = movie

            if created:
                self.stdout.write(self.style.SUCCESS(f"Movie created: {movie.title}"))
            else:
                self.stdout.write(f"Movie updated: {movie.title}")

        # ---------------------------------------------------------------------
        # Create rooms
        # ---------------------------------------------------------------------
        rooms_data = [
            {"name": "Room 1", "total_rows": 5, "total_columns": 6, "is_active": True},
            {"name": "Room 2", "total_rows": 4, "total_columns": 5, "is_active": True},
        ]

        rooms = {}
        for room_data in rooms_data:
            room, created = Room.objects.update_or_create(
                name=room_data["name"],
                defaults=room_data,
            )
            rooms[room.name] = room

            if created:
                self.stdout.write(self.style.SUCCESS(f"Room created: {room.name}"))
            else:
                self.stdout.write(f"Room updated: {room.name}")

        # ---------------------------------------------------------------------
        # Create seats for each room
        # ---------------------------------------------------------------------
        for room in rooms.values():
            created_count = 0

            for row_index in range(room.total_rows):
                row_label = chr(65 + row_index)  # A, B, C...
                for number in range(1, room.total_columns + 1):
                    seat, created = Seat.objects.get_or_create(
                        room=room,
                        row_label=row_label,
                        number=number,
                    )
                    if created:
                        created_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Seats ready for {room.name}. New seats created: {created_count}"
                )
            )

        # ---------------------------------------------------------------------
        # Create sessions
        # ---------------------------------------------------------------------
        now = timezone.now()

        sessions_data = [
            {
                "movie": movies["Dune: Part Two"],
                "room": rooms["Room 1"],
                "start_time": now + timedelta(days=1, hours=2),
                "end_time": now + timedelta(days=1, hours=4, minutes=46),
                "language": "SUB",
                "format_type": "2D",
                "is_active": True,
            },
            {
                "movie": movies["Dune: Part Two"],
                "room": rooms["Room 1"],
                "start_time": now + timedelta(days=2, hours=3),
                "end_time": now + timedelta(days=2, hours=5, minutes=46),
                "language": "DUB",
                "format_type": "IMAX",
                "is_active": True,
            },
            {
                "movie": movies["Inside Out 2"],
                "room": rooms["Room 2"],
                "start_time": now + timedelta(days=1, hours=1),
                "end_time": now + timedelta(days=1, hours=2, minutes=36),
                "language": "DUB",
                "format_type": "2D",
                "is_active": True,
            },
            {
                "movie": movies["The Batman"],
                "room": rooms["Room 2"],
                "start_time": now + timedelta(days=3, hours=2),
                "end_time": now + timedelta(days=3, hours=5),
                "language": "SUB",
                "format_type": "3D",
                "is_active": True,
            },
            {
                "movie": movies["The Batman"],
                "room": rooms["Room 1"],
                "start_time": now - timedelta(days=1, hours=3),
                "end_time": now - timedelta(days=1),
                "language": "SUB",
                "format_type": "2D",
                "is_active": True,
            },
        ]

        created_sessions = []
        for session_data in sessions_data:
            session, created = Session.objects.update_or_create(
                movie=session_data["movie"],
                room=session_data["room"],
                start_time=session_data["start_time"],
                defaults=session_data,
            )
            created_sessions.append(session)

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Session created: {session.movie.title} - {session.start_time}"
                    )
                )
            else:
                self.stdout.write(
                    f"Session updated: {session.movie.title} - {session.start_time}"
                )

        # ---------------------------------------------------------------------
        # Create purchased tickets
        # ---------------------------------------------------------------------
        dune_session = created_sessions[0]
        inside_out_session = created_sessions[2]

        seat_a1_room1 = Seat.objects.get(room=rooms["Room 1"], seat_code="A1")
        seat_a2_room1 = Seat.objects.get(room=rooms["Room 1"], seat_code="A2")
        seat_b1_room2 = Seat.objects.get(room=rooms["Room 2"], seat_code="B1")

        tickets_data = [
            {
                "user": users["matheus"],
                "session": dune_session,
                "seat": seat_a1_room1,
                "status": Ticket.STATUS_ACTIVE,
            },
            {
                "user": users["ana"],
                "session": dune_session,
                "seat": seat_a2_room1,
                "status": Ticket.STATUS_ACTIVE,
            },
            {
                "user": users["carlos"],
                "session": inside_out_session,
                "seat": seat_b1_room2,
                "status": Ticket.STATUS_USED,
            },
        ]

        for ticket_data in tickets_data:
            ticket, created = Ticket.objects.get_or_create(
                session=ticket_data["session"],
                seat=ticket_data["seat"],
                defaults={
                    "user": ticket_data["user"],
                    "ticket_code": str(uuid.uuid4()),
                    "status": ticket_data["status"],
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Ticket created: {ticket.ticket_code} for seat {ticket.seat.seat_code}"
                    )
                )
            else:
                self.stdout.write(
                    f"Ticket already exists for session {ticket.session.id} and seat {ticket.seat.seat_code}"
                )

        # ---------------------------------------------------------------------
        # Create temporary Redis locks
        # ---------------------------------------------------------------------
        locked_seats = [
            {
                "session": dune_session,
                "seat": Seat.objects.get(room=rooms["Room 1"], seat_code="A3"),
                "user": users["matheus"],
            },
            {
                "session": dune_session,
                "seat": Seat.objects.get(room=rooms["Room 1"], seat_code="A4"),
                "user": users["ana"],
            },
        ]

        for item in locked_seats:
            acquired = SeatLockService.acquire_lock(
                session_id=item["session"].id,
                seat_id=item["seat"].id,
                user_id=item["user"].id,
            )

            if acquired:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Redis lock created for session {item['session'].id} seat {item['seat'].seat_code}"
                    )
                )
            else:
                self.stdout.write(
                    f"Redis lock already exists for session {item['session'].id} seat {item['seat'].seat_code}"
                )

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully."))