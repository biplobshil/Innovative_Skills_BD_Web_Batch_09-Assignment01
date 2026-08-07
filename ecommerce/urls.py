from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.generic import RedirectView

from store.views import signup_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("store.urls")),           # JSON REST API (DRF)
    path("products/", include("store.template_urls")),  # server-rendered Django-template views

    # Auth — login/logout are Django's built-in views with our own templates;
    # signup is a small custom view in store/views.py
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("accounts/signup/", signup_view, name="signup"),

    path("", RedirectView.as_view(pattern_name="store:product-list", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
