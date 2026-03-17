from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class UserAuthenticationTests(APITestCase):
    """
    Test the authentication flow for CASE 1:
    - register
    - login
    - refresh
    - authenticated user profile
    """

    def setUp(self):
        """
        I define the most common URLs used in authentication tests.
        """
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.refresh_url = reverse("refresh")
        self.me_url = reverse("me")

        self.user_data = {
            "username": "matheus",
            "email": "matheus@email.com",
            "password": "12345678",
        }

    def test_user_can_register_successfully(self):
        """
        I verify that a new user can register successfully.
        """
        response = self.client.post(self.register_url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.first().username, "matheus")
        self.assertNotIn("password", response.data)

    def test_user_cannot_register_with_existing_email(self):
        """
        I verify that the API blocks duplicated e-mails.
        """
        User.objects.create_user(
            username="existing_user",
            email="matheus@email.com",
            password="12345678"
        )

        payload = {
            "username": "new_user",
            "email": "matheus@email.com",
            "password": "12345678",
        }

        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_user_cannot_register_with_existing_username(self):
        """
        I verify that the API blocks duplicated usernames.
        """
        User.objects.create_user(
            username="matheus",
            email="other@email.com",
            password="12345678"
        )

        payload = {
            "username": "matheus",
            "email": "new@email.com",
            "password": "12345678",
        }

        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_user_can_login_and_receive_tokens(self):
        """
        I verify that a valid user can log in and receive JWT tokens.
        """
        User.objects.create_user(**self.user_data)

        payload = {
            "username": self.user_data["username"],
            "password": self.user_data["password"],
        }

        response = self.client.post(self.login_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_user_cannot_login_with_invalid_password(self):
        """
        I verify that invalid credentials are rejected.
        """
        User.objects.create_user(**self.user_data)

        payload = {
            "username": self.user_data["username"],
            "password": "wrong-password",
        }

        response = self.client.post(self.login_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_refresh_access_token(self):
        """
        I verify that a valid refresh token can generate a new access token.
        """
        User.objects.create_user(**self.user_data)

        login_response = self.client.post(
            self.login_url,
            {
                "username": self.user_data["username"],
                "password": self.user_data["password"],
            },
            format="json"
        )

        refresh_token = login_response.data["refresh"]

        response = self.client.post(
            self.refresh_url,
            {"refresh": refresh_token},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_authenticated_user_can_access_me_endpoint(self):
        """
        I verify that an authenticated user can retrieve their own profile.
        """
        user = User.objects.create_user(**self.user_data)

        login_response = self.client.post(
            self.login_url,
            {
                "username": self.user_data["username"],
                "password": self.user_data["password"],
            },
            format="json"
        )

        access_token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], user.username)
        self.assertEqual(response.data["email"], user.email)

    def test_unauthenticated_user_cannot_access_me_endpoint(self):
        """
        I verify that authentication is required for the profile endpoint.
        """
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)