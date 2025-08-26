"""
Monitoring URLs
"""
from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    path('', views.home, name='home'),
    path('metrics/', views.metrics_view, name='metrics'),
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('services/', views.services_status, name='services_status'),
]