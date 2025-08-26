"""
Router Manager URL Configuration
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),  # Add Django auth URLs
    path("", RedirectView.as_view(url="/dashboard/", permanent=False)),
    path("dashboard/", include("dashboard.urls")),
    path("firewall/", include("nftables_mgr.urls")),
    path("network/", include("network.urls")),
    path("vpn/", include("vpn.urls")),
    path("monitoring/", include("monitoring.urls")),
]

# Add media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customize admin site headers
admin.site.site_header = "Router Manager Administration"
admin.site.site_title = "Router Manager Admin"
admin.site.index_title = "Welcome to Router Manager Administration"
