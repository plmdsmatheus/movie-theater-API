from django.shortcuts import render
from rest_framework import generics, permissions
from .serializers import RegisterSerializer, UserSerializer
from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=['Users'],
    summary='Register a new user',
    description='Creates a new user account with username, email and password.'
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=['Users'],
    summary='Get authenticated user',
    description='Returns the currently authenticated user.'
)
class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user