from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Main URLs for the project
urlpatterns = [
    path('admin/', admin.site.urls),

    # schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # swagger ui
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # redoc
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # app routes
    path('api/users/', include('apps.users.urls')),
]
