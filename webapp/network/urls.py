"""
Network management URLs
"""

from django.urls import path

from . import views

app_name = "network"

urlpatterns = [
    path("", views.home, name="home"),
    path("interfaces/", views.interfaces_list, name="interfaces_list"),
    path(
        "interfaces/<str:interface_name>/",
        views.interface_detail,
        name="interface_detail",
    ),
    path("routing/", views.routing_table, name="routing_table"),
    path("static-routes/", views.static_routes_list, name="static_routes_list"),
    path("static-routes/add/", views.add_static_route_view, name="add_static_route"),
    path("static-routes/<int:route_id>/edit/", views.edit_static_route, name="edit_static_route"),
    path("static-routes/<int:route_id>/delete/", views.delete_static_route_view, name="delete_static_route"),
    path("settings/", views.system_settings, name="system_settings"),
    path("api/status/", views.network_status_api, name="network_status_api"),
]
