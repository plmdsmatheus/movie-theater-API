from django.contrib import admin
from django.urls import path, include

# Main URLs for the project
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.users.urls')),
    path('api/', include('apps.movies.urls')),
]
