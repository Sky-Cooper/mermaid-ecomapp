from django.contrib import admin
from django.urls import path, include
from core.views import (
    CustomerRegistrationView,
    CustomTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutView,
    GoogleLogin,  # Import the new view
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # Email/Password Auth
    path("auth/register/", CustomerRegistrationView.as_view(), name="register"),
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", CookieTokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    # Social Auth
    path("auth/google/", GoogleLogin.as_view(), name="google_login"),
    path("api/", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
