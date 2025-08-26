"""
nftables management URLs
"""
from django.urls import path
from . import views

app_name = 'nftables'

urlpatterns = [
    path('', views.home, name='home'),
    path('rules/', views.rules_list, name='rules_list'),
    path('rules/add/', views.add_rule, name='add_rule'),
    path('port-forward/', views.port_forward_list, name='port_forward_list'),
    path('port-forward/add/', views.add_port_forward, name='add_port_forward'),
]