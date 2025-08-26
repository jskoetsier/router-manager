"""
Dashboard URL configuration
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('api/status/', views.system_status_api, name='status_api'),
    path('alerts/', views.alerts_view, name='alerts'),
    path('alerts/acknowledge/<int:alert_id>/', views.acknowledge_alert, name='acknowledge_alert'),
    path('activity/', views.activity_log, name='activity_log'),
    path('system/', views.system_info_view, name='system_info'),
    path('settings/', views.settings_view, name='settings'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
]