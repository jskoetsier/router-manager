"""
Network management URLs
"""
from django.urls import path
from . import views

app_name = 'network'

urlpatterns = [
    path('', views.home, name='home'),
    path('interfaces/', views.interfaces_list, name='interfaces_list'),
    path('interfaces/<str:interface_name>/', views.interface_detail, name='interface_detail'),
    path('routing/', views.routing_table, name='routing_table'),
    path('settings/', views.system_settings, name='system_settings'),
    path('api/status/', views.network_status_api, name='network_status_api'),
]