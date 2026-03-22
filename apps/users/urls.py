from django.urls import path
from .views import RegisterView, LoginView, RefreshView, MeView

''' URL patterns for user authentication and profile management endpoints.
These routes handle user registration, authentication (JWT), token refresh,
and retrieval of the currently authenticated user.
'''

urlpatterns = [
    # Endpoint for creating a new user account.
    # Expects username, email, and password in the request body.
    path('register/', RegisterView.as_view(), name='register'),

    # Endpoint for user authentication.
    # Returns JWT access and refresh tokens upon successful login.
    path('login/', LoginView.as_view(), name='login'),

    # Endpoint to refresh the access token using a valid refresh token.
    # Typically used when the access token expires.
    path('refresh/', RefreshView.as_view(), name='refresh'),

    # Endpoint to retrieve the currently authenticated user's data.
    # Requires a valid JWT access token in the Authorization header.
    path('me/', MeView.as_view(), name='me'),
]