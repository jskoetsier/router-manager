from django.urls import path
from . import views

app_name = 'nginx_mgr'

urlpatterns = [
    # Main listing and navigation
    path('', views.nginx_list, name='list'),
    path('status/', views.nginx_status, name='status'),
    path('logs/', views.deployment_logs, name='logs'),

    # Configuration management
    path('create/', views.nginx_create, name='create'),
    path('quick-create/', views.nginx_quick_create, name='quick_create'),
    path('<int:pk>/', views.nginx_detail, name='detail'),
    path('<int:pk>/edit/', views.nginx_edit, name='edit'),
    path('<int:pk>/delete/', views.nginx_delete, name='delete'),

    # Deployment actions
    path('<int:pk>/deploy/', views.nginx_deploy, name='deploy'),
    path('<int:pk>/undeploy/', views.nginx_undeploy, name='undeploy'),

    # SSL certificate management
    path('<int:pk>/ssl/renew/', views.ssl_renew, name='ssl_renew'),

    # AJAX endpoints
    path('<int:pk>/status/ajax/', views.ajax_config_status, name='ajax_status'),
]
