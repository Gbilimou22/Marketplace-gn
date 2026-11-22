"""
URL Configuration for Marketplace Guinée.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/profile/", RedirectView.as_view(pattern_name="shops:seller_dashboard", permanent=False)),
    path("accounts/", include("allauth.urls")),
    path("boutiques/", include("apps.shops.urls", namespace="shops")),
    path("articles/", include("apps.catalog.urls", namespace="catalog")),
    path("", RedirectView.as_view(pattern_name="catalog:list", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
