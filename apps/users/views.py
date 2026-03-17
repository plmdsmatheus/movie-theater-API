from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    LoginSerializer,
    TokenResponseSerializer,
    RefreshTokenRequestSerializer,
    AccessTokenResponseSerializer,
)


@extend_schema(
    tags=['Users'],
    summary='Register a new user',
    description='Creates a new user account with username, email and password.',
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(
            response=UserSerializer,
            description='User created successfully.'
        ),
        400: OpenApiResponse(description='Validation error.')
    },
    examples=[
        OpenApiExample(
            'Register request',
            value={
                'username': 'matheus',
                'email': 'matheus@email.com',
                'password': '12345678'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Register response',
            value={
                'id': 1,
                'username': 'matheus',
                'email': 'matheus@email.com'
            },
            response_only=True,
            status_codes=['201'],
        ),
    ],
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=['Users'],
    summary='Login with username and password',
    description='Returns JWT access and refresh tokens for an authenticated user.',
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(
            response=TokenResponseSerializer,
            description='JWT tokens generated successfully.'
        ),
        401: OpenApiResponse(description='Invalid credentials.')
    },
    examples=[
        OpenApiExample(
            'Login request',
            value={
                'username': 'matheus',
                'password': '12345678'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Login response',
            value={
                'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh',
                'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access'
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=['Users'],
    summary='Refresh access token',
    description='Receives a refresh token and returns a new access token.',
    request=RefreshTokenRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=AccessTokenResponseSerializer,
            description='New access token generated successfully.'
        ),
        401: OpenApiResponse(description='Invalid or expired refresh token.')
    },
    examples=[
        OpenApiExample(
            'Refresh request',
            value={
                'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Refresh response',
            value={
                'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_access'
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=['Users'],
    summary='Get authenticated user',
    description='Returns the currently authenticated user.',
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description='Authenticated user returned successfully.'
        ),
        401: OpenApiResponse(description='Authentication credentials were not provided or are invalid.')
    },
    examples=[
        OpenApiExample(
            'Authenticated user response',
            value={
                'id': 1,
                'username': 'matheus',
                'email': 'matheus@email.com'
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user