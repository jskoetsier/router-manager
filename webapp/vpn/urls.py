"""
VPN management URLs
"""
from django.urls import path
from . import views

app_name = 'vpn'

urlpatterns = [
    path('', views.home, name='home'),
    path('tunnels/', views.tunnels_list, name='tunnels_list'),
    path('tunnels/add/', views.add_tunnel, name='add_tunnel'),
    path('tunnels/edit/<int:tunnel_id>/', views.edit_tunnel, name='edit_tunnel'),
    path('tunnels/delete/<int:tunnel_id>/', views.delete_tunnel, name='delete_tunnel'),
    path('tunnels/control/<int:tunnel_id>/<str:action>/', views.tunnel_control, name='tunnel_control'),
    path('tunnels/status/<int:tunnel_id>/', views.tunnel_status_api, name='tunnel_status_api'),
    path('quick-setup/', views.quick_setup, name='quick_setup'),
    path('certificates/', views.certificates_list, name='certificates_list'),
    path('users/', views.users_list, name='users_list'),
]