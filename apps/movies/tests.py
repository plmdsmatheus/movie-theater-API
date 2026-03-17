from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.movies.models import Movie, Room, Seat, Session, Ticket


class MovieBaseTestCase(APITestCase):
    """
    I centralize common setup data shared across movie-related test cases.
    """

    def setUp(self):
        """
        I create reusable fixtures for movies, rooms, seats, sessions, and users.
        """
        self.user = User.objects.create_user(
            username="matheus",
            email="matheus@email.com",
            password="12345678"
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@email.com",
            password="12345678"
        )

        self.movie = Movie.objects.create(
            title="Dune: Part Two",
            description="Sci-fi movie",
            duration_minutes=166,
            rating="14",
            poster_url="https://example.com/dune.jpg",
            is_active=True
        )

        self.inactive_movie = Movie.objects.create(
            title="Old Movie",
            description="Inactive movie",
            duration_minutes=120,
            rating="16",
            poster_url="https://example.com/old.jpg",
            is_active=False
        )

        self.room = Room.objects.create(
            name="Room 1",
            total_rows=2,
            total_columns=3,
            is_active=True
        )

        self.seat_a1 = Seat.objects.create(room=self.room, row_label="A", number=1)
        self.seat_a2 = Seat.objects.create(room=self.room, row_label="A", number=2)
        self.seat_a3 = Seat.objects.create(room=self.room, row_label="A", number=3)
        self.seat_b1 = Seat.objects.create(room=self.room, row_label="B", number=1)
        self.seat_b2 = Seat.objects.create(room=self.room, row_label="B", number=2)
        self.seat_b3 = Seat.objects.create(room=self.room, row_label="B", number=3)

        self.upcoming_session = Session.objects.create(
            movie=self.movie,
            room=self.room,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
            language="SUB",
            format_type="2D",
            is_active=True
        )

        self.past_session = Session.objects.create(
            movie=self.movie,
            room=self.room,
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() - timedelta(days=1, hours=-3),
            language="SUB",
            format_type="2D",
            is_active=True
        )

        self.inactive_session = Session.objects.create(
            movie=self.movie,
            room=self.room,
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=3),
            language="DUB",
            format_type="3D",
            is_active=False
        )

        self.inactive_movie_session = Session.objects.create(
            movie=self.inactive_movie,
            room=self.room,
            start_time=timezone.now() + timedelta(days=3),
            end_time=timezone.now() + timedelta(days=3, hours=2),
            language="SUB",
            format_type="2D",
            is_active=True
        )

        self.movie_list_url = reverse("movie-list")
        self.movie_sessions_url = reverse("movie-sessions", kwargs={"movie_id": self.movie.id})
        self.seat_map_url = reverse("session-seat-map", kwargs={"session_id": self.upcoming_session.id})
        self.reserve_seat_url = reverse("session-seat-reserve", kwargs={"session_id": self.upcoming_session.id})
        self.release_seat_url = reverse("session-seat-release", kwargs={"session_id": self.upcoming_session.id})

    def authenticate(self, user=None):
        """
        I authenticate the test client using JWT.
        """
        target_user = user or self.user

        login_response = self.client.post(
            reverse("login"),
            {
                "username": target_user.username,
                "password": "12345678",
            },
            format="json"
        )

        access_token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

class MovieListTests(MovieBaseTestCase):
    """
    I test CASE 2: listing all available movies.
    """

    def test_any_user_can_list_available_movies(self):
        """
        I verify that the movie list endpoint is public.
        """
        response = self.client.get(self.movie_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie.title)

    def test_movie_list_returns_only_active_movies(self):
        """
        I verify that inactive movies are excluded from the public catalog.
        """
        response = self.client.get(self.movie_list_url)

        returned_titles = [movie["title"] for movie in response.data["results"]]

        self.assertIn(self.movie.title, returned_titles)
        self.assertNotIn(self.inactive_movie.title, returned_titles)

class MovieSessionListTests(MovieBaseTestCase):
    """
    I test CASE 3: listing available sessions for a specific movie.
    """

    def test_any_user_can_list_available_sessions_for_a_movie(self):
        """
        I verify that the session list endpoint is public.
        """
        response = self.client.get(self.movie_sessions_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_list_returns_only_active_and_upcoming_sessions(self):
        """
        I verify that the endpoint excludes past and inactive sessions.
        """
        response = self.client.get(self.movie_sessions_url)

        returned_session_ids = [session["id"] for session in response.data["results"]]

        self.assertIn(self.upcoming_session.id, returned_session_ids)
        self.assertNotIn(self.past_session.id, returned_session_ids)
        self.assertNotIn(self.inactive_session.id, returned_session_ids)

    def test_session_list_excludes_sessions_from_inactive_movies(self):
        """
        I verify that sessions from inactive movies are not returned.
        """
        url = reverse("movie-sessions", kwargs={"movie_id": self.inactive_movie.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

class SessionSeatMapTests(MovieBaseTestCase):
    """
    I test CASE 4: seat map visualization for a movie session.
    """

    @patch("apps.movies.views.SeatLockService.list_reserved_seat_ids_for_session")
    def test_seat_map_marks_all_available_when_no_ticket_or_lock(self, mock_reserved_seats):
        """
        I verify that seats are marked as AVAILABLE when no lock or ticket exists.
        """
        mock_reserved_seats.return_value = set()

        response = self.client.get(self.seat_map_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["session_id"], self.upcoming_session.id)

        flat_seats = [seat for row in response.data["seat_map"] for seat in row]
        statuses = {seat["seat_code"]: seat["status"] for seat in flat_seats}

        self.assertEqual(statuses["A1"], "AVAILABLE")
        self.assertEqual(statuses["A2"], "AVAILABLE")
        self.assertEqual(statuses["B1"], "AVAILABLE")

    @patch("apps.movies.views.SeatLockService.list_reserved_seat_ids_for_session")
    def test_seat_map_marks_reserved_and_purchased_correctly(self, mock_reserved_seats):
        """
        I verify that the seat map correctly prioritizes PURCHASED over RESERVED.
        """
        Ticket.objects.create(
            user=self.user,
            session=self.upcoming_session,
            seat=self.seat_b1,
            ticket_code="ticket-b1",
            status=Ticket.STATUS_ACTIVE
        )

        mock_reserved_seats.return_value = {self.seat_a2.id, self.seat_b1.id}

        response = self.client.get(self.seat_map_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        flat_seats = [seat for row in response.data["seat_map"] for seat in row]
        statuses = {seat["seat_code"]: seat["status"] for seat in flat_seats}

        self.assertEqual(statuses["A2"], "RESERVED")
        self.assertEqual(statuses["B1"], "PURCHASED")

    def test_seat_map_returns_404_for_invalid_session(self):
        """
        I verify that an invalid session returns not found.
        """
        url = reverse("session-seat-map", kwargs={"session_id": 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class SessionSeatReservationTests(MovieBaseTestCase):
    """
    I test CASE 5: temporary seat reservation using Redis locks.
    """

    @patch("apps.movies.views.SeatLockService.acquire_lock")
    @patch("apps.movies.views.SeatLockService.get_lock_ttl")
    def test_authenticated_user_can_reserve_seat_successfully(self, mock_get_ttl, mock_acquire_lock):
        """
        I verify that an authenticated user can reserve an available seat.
        """
        self.authenticate()

        mock_acquire_lock.return_value = True
        mock_get_ttl.return_value = 600

        response = self.client.post(
            self.reserve_seat_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "RESERVED")
        self.assertEqual(response.data["seat_id"], self.seat_a1.id)
        self.assertEqual(response.data["expires_in_seconds"], 600)

    def test_unauthenticated_user_cannot_reserve_seat(self):
        """
        I verify that seat reservation requires authentication.
        """
        response = self.client.post(
            self.reserve_seat_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_reserve_seat_that_was_already_purchased(self):
        """
        I verify that a purchased seat cannot be reserved again.
        """
        self.authenticate()

        Ticket.objects.create(
            user=self.user,
            session=self.upcoming_session,
            seat=self.seat_a1,
            ticket_code="ticket-a1",
            status=Ticket.STATUS_ACTIVE
        )

        response = self.client.post(
            self.reserve_seat_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["detail"], "This seat has already been purchased.")

    @patch("apps.movies.views.SeatLockService.acquire_lock")
    @patch("apps.movies.views.SeatLockService.get_lock_data")
    @patch("apps.movies.views.SeatLockService.get_lock_ttl")
    def test_user_cannot_reserve_seat_that_is_already_locked(
        self,
        mock_get_ttl,
        mock_get_lock_data,
        mock_acquire_lock
    ):
        """
        I verify that the API returns conflict when the seat is already reserved.
        """
        self.authenticate()

        mock_acquire_lock.return_value = False
        mock_get_lock_data.return_value = {
            "user_id": self.other_user.id,
            "session_id": self.upcoming_session.id,
            "seat_id": self.seat_a1.id,
        }
        mock_get_ttl.return_value = 480

        response = self.client.post(
            self.reserve_seat_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["detail"], "This seat is currently reserved.")
        self.assertEqual(response.data["expires_in_seconds"], 480)

    def test_user_cannot_reserve_seat_from_another_room(self):
        """
        I verify that a seat must belong to the session room.
        """
        self.authenticate()

        other_room = Room.objects.create(
            name="Room 2",
            total_rows=1,
            total_columns=1,
            is_active=True
        )
        foreign_seat = Seat.objects.create(room=other_room, row_label="A", number=1)

        response = self.client.post(
            self.reserve_seat_url,
            {"seat_id": foreign_seat.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class SessionSeatReleaseTests(MovieBaseTestCase):
    """
    I test the optional lock release endpoint.
    """

    @patch("apps.movies.views.SeatLockService.get_lock_data")
    @patch("apps.movies.views.SeatLockService.release_lock")
    def test_user_can_release_own_lock(self, mock_release_lock, mock_get_lock_data):
        """
        I verify that a user can release a lock they own.
        """
        self.authenticate()

        mock_get_lock_data.return_value = {
            "user_id": self.user.id,
            "session_id": self.upcoming_session.id,
            "seat_id": self.seat_a1.id,
        }
        mock_release_lock.return_value = True

        response = self.client.post(
            self.release_seat_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "AVAILABLE")

    @patch("apps.movies.views.SeatLockService.get_lock_data")
    def test_user_cannot_release_another_users_lock(self, mock_get_lock_data):
        """
        I verify that a user cannot release another user's lock.
        """
        self.authenticate()

        mock_get_lock_data.return_value = {
            "user_id": self.other_user.id,
            "session_id": self.upcoming_session.id,
            "seat_id": self.seat_a1.id,
        }

        response = self.client.post(
            self.release_seat_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_release_lock(self):
        """
        I verify that lock release requires authentication.
        """
        response = self.client.post(
            self.release_seat_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class SessionSeatCheckoutTests(MovieBaseTestCase):
    """
    I test CASE 6: checkout and ticket generation.
    """

    def setUp(self):
        super().setUp()
        self.checkout_url = reverse(
            "session-seat-checkout",
            kwargs={"session_id": self.upcoming_session.id}
        )

    def authenticate(self, user=None):
        super().authenticate(user=user)

    @patch("apps.movies.views.SeatLockService.get_lock_data")
    @patch("apps.movies.views.SeatLockService.release_lock")
    def test_authenticated_user_can_checkout_reserved_seat(self, mock_release_lock, mock_get_lock_data):
        """
        I verify that an authenticated user can convert their own lock into a ticket.
        """
        self.authenticate()

        mock_get_lock_data.return_value = {
            "user_id": self.user.id,
            "session_id": self.upcoming_session.id,
            "seat_id": self.seat_a1.id,
        }
        mock_release_lock.return_value = True

        response = self.client.post(
            self.checkout_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Ticket generated successfully.")
        self.assertEqual(response.data["ticket"]["seat_code"], "A1")
        self.assertEqual(Ticket.objects.count(), 1)

    def test_unauthenticated_user_cannot_checkout(self):
        """
        I verify that checkout requires authentication.
        """
        response = self.client.post(
            self.checkout_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.movies.views.SeatLockService.get_lock_data")
    def test_user_cannot_checkout_without_active_lock(self, mock_get_lock_data):
        """
        I verify that checkout fails when no active lock exists.
        """
        self.authenticate()

        mock_get_lock_data.return_value = None

        response = self.client.post(
            self.checkout_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No active seat lock was found for this seat.")

    @patch("apps.movies.views.SeatLockService.get_lock_data")
    def test_user_cannot_checkout_another_users_lock(self, mock_get_lock_data):
        """
        I verify that a user cannot checkout a seat locked by another user.
        """
        self.authenticate()

        mock_get_lock_data.return_value = {
            "user_id": self.other_user.id,
            "session_id": self.upcoming_session.id,
            "seat_id": self.seat_a1.id,
        }

        response = self.client.post(
            self.checkout_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "You cannot checkout a seat reserved by another user.")

    @patch("apps.movies.views.SeatLockService.get_lock_data")
    def test_user_cannot_checkout_purchased_seat(self, mock_get_lock_data):
        """
        I verify that checkout fails if the seat has already been purchased.
        """
        self.authenticate()

        Ticket.objects.create(
            user=self.user,
            session=self.upcoming_session,
            seat=self.seat_a1,
            ticket_code="existing-ticket",
            status=Ticket.STATUS_ACTIVE
        )

        mock_get_lock_data.return_value = {
            "user_id": self.user.id,
            "session_id": self.upcoming_session.id,
            "seat_id": self.seat_a1.id,
        }

        response = self.client.post(
            self.checkout_url,
            {"seat_id": self.seat_a1.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["detail"], "This seat has already been purchased.")

    @patch("apps.movies.views.SeatLockService.get_lock_data")
    def test_user_cannot_checkout_seat_from_another_room(self, mock_get_lock_data):
        """
        I verify that checkout fails if the seat does not belong to the session room.
        """
        self.authenticate()

        other_room = Room.objects.create(
            name="Room 2",
            total_rows=1,
            total_columns=1,
            is_active=True
        )
        foreign_seat = Seat.objects.create(room=other_room, row_label="A", number=1)

        mock_get_lock_data.return_value = {
            "user_id": self.user.id,
            "session_id": self.upcoming_session.id,
            "seat_id": foreign_seat.id,
        }

        response = self.client.post(
            self.checkout_url,
            {"seat_id": foreign_seat.id},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
class MyTicketsListTests(MovieBaseTestCase):
    """
    I test CASE 7: the authenticated user's ticket portal.
    """

    def setUp(self):
        super().setUp()
        self.my_tickets_url = reverse("my-tickets")

        self.future_ticket = Ticket.objects.create(
            user=self.user,
            session=self.upcoming_session,
            seat=self.seat_a1,
            ticket_code="future-ticket",
            status=Ticket.STATUS_ACTIVE
        )

        self.past_ticket = Ticket.objects.create(
            user=self.user,
            session=self.past_session,
            seat=self.seat_a2,
            ticket_code="past-ticket",
            status=Ticket.STATUS_ACTIVE
        )

        self.used_ticket = Ticket.objects.create(
            user=self.user,
            session=self.upcoming_session,
            seat=self.seat_a3,
            ticket_code="used-ticket",
            status=Ticket.STATUS_USED
        )

        self.other_user_ticket = Ticket.objects.create(
            user=self.other_user,
            session=self.upcoming_session,
            seat=self.seat_b1,
            ticket_code="other-user-ticket",
            status=Ticket.STATUS_ACTIVE
        )

    def test_authenticated_user_can_list_all_own_tickets(self):
        """
        I verify that an authenticated user can list only their own tickets.
        """
        self.authenticate()

        response = self.client.get(self.my_tickets_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        returned_codes = [ticket["ticket_code"] for ticket in response.data["results"]]
        self.assertIn("future-ticket", returned_codes)
        self.assertIn("past-ticket", returned_codes)
        self.assertIn("used-ticket", returned_codes)
        self.assertNotIn("other-user-ticket", returned_codes)

    def test_user_can_filter_only_active_upcoming_tickets(self):
        """
        I verify that the active filter returns only upcoming active tickets.
        """
        self.authenticate()

        response = self.client.get(f"{self.my_tickets_url}?type=active")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        returned_codes = [ticket["ticket_code"] for ticket in response.data]
        self.assertIn("future-ticket", returned_codes)
        self.assertNotIn("past-ticket", returned_codes)
        self.assertNotIn("used-ticket", returned_codes)

    def test_user_can_filter_ticket_history(self):
        """
        I verify that the history filter returns the complete ticket history.
        """
        self.authenticate()

        response = self.client.get(f"{self.my_tickets_url}?type=history")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_unauthenticated_user_cannot_access_my_tickets(self):
        """
        I verify that authentication is required for the ticket portal.
        """
        response = self.client.get(self.my_tickets_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)