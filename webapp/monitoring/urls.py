"""
Monitoring URLs
"""

from django.urls import path

from . import views

app_name = "monitoring"

urlpatterns = [
    # Dashboard
    path("", views.home, name="home"),
    
    # Metrics and Analytics
    path("metrics/", views.metrics_view, name="metrics"),
    
    # Alerts Management
    path("alerts/", views.alerts_list, name="alerts_list"),
    path("alerts/create/", views.alert_create, name="alert_create"),
    path("alerts/<int:alert_id>/edit/", views.alert_edit, name="alert_edit"),
    path("alerts/<int:alert_id>/toggle/", views.alert_toggle, name="alert_toggle"),
    
    # Services Monitoring
    path("services/", views.services_status, name="services_status"),
    
    # Network Monitoring
    path("network/interfaces/", views.network_interfaces, name="network_interfaces"),
    path("network/connections/", views.connections_monitor, name="connections_monitor"),
    
    # Logs
    path("logs/", views.logs_view, name="logs"),
    
    # Settings
    path("settings/", views.settings_view, name="settings"),
    
    # API Endpoints
    path("api/metrics/", views.api_metrics_data, name="api_metrics_data"),
    path("api/status/", views.api_system_status, name="api_system_status"),
    
    # Actions
    path("actions/collect/", views.force_metrics_collection, name="force_collection"),
]
