"""
Network management views
"""

import json

from dashboard.utils import log_user_activity
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Route, NetworkInterface
from .forms import RouteForm
from .utils import (
    configure_basic_nat,
    get_ip_forwarding_status,
    get_nat_status,
    get_network_interfaces,
    get_nftables_rules,
    get_routing_table,
    set_ip_forwarding,
    add_static_route,
    delete_static_route,
    make_route_persistent,
    remove_persistent_route,
)


@login_required
def home(request):
    """Network management home"""
    # Get current system status
    forwarding_status = get_ip_forwarding_status()
    nat_status = get_nat_status()
    interfaces = get_network_interfaces()

    context = {
        "forwarding_status": forwarding_status,
        "nat_status": nat_status,
        "interfaces": interfaces,
        "interface_count": len(interfaces) if "error" not in interfaces else 0,
    }
    return render(request, "network/home.html", context)


@login_required
def interfaces_list(request):
    """List network interfaces"""
    interfaces = get_network_interfaces()
    context = {"interfaces": interfaces}
    return render(request, "network/interfaces_list.html", context)


@login_required
def interface_detail(request, interface_name):
    """Interface configuration details"""
    interfaces = get_network_interfaces()
    interface = interfaces.get(interface_name, {})

    context = {"interface_name": interface_name, "interface": interface}
    return render(request, "network/interface_detail.html", context)


@login_required
def routing_table(request):
    """Network routing table"""
    routes = get_routing_table()
    context = {"routes": routes}
    return render(request, "network/routing_table.html", context)


@login_required
def system_settings(request):
    """System network settings"""
    if request.method == "POST":
        try:
            # Handle IP forwarding toggle
            if "toggle_ip_forwarding" in request.POST:
                ipv4_enabled = request.POST.get("ipv4_forwarding") == "on"
                ipv6_enabled = request.POST.get("ipv6_forwarding") == "on"

                results = set_ip_forwarding(ipv4_enabled, ipv6_enabled, permanent=True)

                success_count = sum(1 for _, success, _ in results if success)
                total_count = len(results)

                if success_count == total_count:
                    messages.success(
                        request, "IP forwarding settings updated successfully."
                    )
                    log_user_activity(
                        request.user,
                        f"Updated IP forwarding: IPv4={ipv4_enabled}, IPv6={ipv6_enabled}",
                        request.META.get("REMOTE_ADDR", ""),
                        True,
                    )
                else:
                    failed_operations = [
                        name for name, success, error in results if not success
                    ]
                    messages.warning(
                        request,
                        f'Some operations failed: {", ".join(failed_operations)}',
                    )
                    log_user_activity(
                        request.user,
                        f"Partially updated IP forwarding settings",
                        request.META.get("REMOTE_ADDR", ""),
                        False,
                    )

            # Handle NAT configuration
            elif "toggle_nat" in request.POST:
                nat_enabled = request.POST.get("nat_enabled") == "on"
                interface = request.POST.get("nat_interface", "eth0")

                results = configure_basic_nat(interface, nat_enabled)

                success_count = sum(1 for _, success, _ in results if success)
                total_count = len(results)

                if success_count == total_count:
                    messages.success(
                        request,
                        f'NAT {"enabled" if nat_enabled else "disabled"} successfully.',
                    )
                    log_user_activity(
                        request.user,
                        f'{"Enabled" if nat_enabled else "Disabled"} NAT on interface {interface}',
                        request.META.get("REMOTE_ADDR", ""),
                        True,
                    )
                else:
                    messages.error(
                        request, "Failed to configure NAT. Please check system logs."
                    )
                    log_user_activity(
                        request.user,
                        f"Failed to configure NAT",
                        request.META.get("REMOTE_ADDR", ""),
                        False,
                    )

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            log_user_activity(
                request.user,
                f"Network settings error: {str(e)}",
                request.META.get("REMOTE_ADDR", ""),
                False,
            )

        return redirect("network:system_settings")

    # GET request - show current settings
    forwarding_status = get_ip_forwarding_status()
    nat_status = get_nat_status()
    interfaces = get_network_interfaces()
    nftables_info = get_nftables_rules()

    # Calculate interface statistics
    interface_count = 0
    active_interface_count = 0
    if interfaces and "error" not in interfaces:
        interface_count = len(interfaces)
        active_interface_count = sum(
            1 for iface in interfaces.values() if iface.get("state") == "UP"
        )

    context = {
        "forwarding_status": forwarding_status,
        "nat_status": nat_status,
        "interfaces": interfaces,
        "nftables_info": nftables_info,
        "interface_count": interface_count,
        "active_interface_count": active_interface_count,
    }
    return render(request, "network/system_settings.html", context)


@login_required
def static_routes_list(request):
    """List static routes"""
    # Get database routes
    db_routes = Route.objects.all().order_by('metric', 'destination')

    # Get system routes for comparison
    system_routes = get_routing_table()

    context = {
        'db_routes': db_routes,
        'system_routes': system_routes,
        'page_title': 'Static Routes'
    }

    return render(request, 'network/static_routes_list.html', context)


@login_required
def add_static_route_view(request):
    """Add new static route"""
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            try:
                route = form.save(commit=False)
                route.created_by = request.user

                # Apply route to system
                result = add_static_route(
                    route.destination,
                    route.gateway,
                    route.interface.name if route.interface else None,
                    route.metric
                )

                if result['success']:
                    # Make route persistent
                    if route.interface:
                        persist_result = make_route_persistent(
                            route.destination,
                            route.gateway,
                            route.interface.name,
                            route.metric
                        )

                        if not persist_result['success']:
                            messages.warning(request, f'Route added but persistence failed: {persist_result.get("error", "Unknown error")}')

                    # Save to database
                    route.save()

                    messages.success(request, f'Static route "{route.destination}" added successfully!')
                    log_user_activity(
                        request.user,
                        f'Added static route: {route.destination} via {route.gateway}',
                        request.META.get('REMOTE_ADDR', ''),
                        True
                    )
                    return redirect('network:static_routes_list')
                else:
                    messages.error(request, f'Failed to add route: {result.get("error", "Unknown error")}')

            except Exception as e:
                messages.error(request, f'Failed to add static route: {str(e)}')
                log_user_activity(
                    request.user,
                    f'Failed to add static route: {str(e)}',
                    request.META.get('REMOTE_ADDR', ''),
                    False
                )
    else:
        form = RouteForm()

    context = {
        'form': form,
        'page_title': 'Add Static Route'
    }

    return render(request, 'network/add_static_route.html', context)


@login_required
def edit_static_route(request, route_id):
    """Edit existing static route"""
    route = get_object_or_404(Route, id=route_id)

    if request.method == 'POST':
        form = RouteForm(request.POST, instance=route)
        if form.is_valid():
            try:
                # Remove old route first
                delete_result = delete_static_route(
                    route.destination,
                    route.gateway,
                    route.interface.name if route.interface else None
                )

                # Remove from persistent config
                if route.interface:
                    remove_persistent_route(route.destination, route.interface.name)

                # Update route object
                updated_route = form.save(commit=False)

                # Apply new route to system
                result = add_static_route(
                    updated_route.destination,
                    updated_route.gateway,
                    updated_route.interface.name if updated_route.interface else None,
                    updated_route.metric
                )

                if result['success']:
                    # Make route persistent
                    if updated_route.interface:
                        persist_result = make_route_persistent(
                            updated_route.destination,
                            updated_route.gateway,
                            updated_route.interface.name,
                            updated_route.metric
                        )

                        if not persist_result['success']:
                            messages.warning(request, f'Route updated but persistence failed: {persist_result.get("error", "Unknown error")}')

                    # Save to database
                    updated_route.save()

                    messages.success(request, f'Static route "{route.destination}" updated successfully!')
                    log_user_activity(
                        request.user,
                        f'Updated static route: {route.destination}',
                        request.META.get('REMOTE_ADDR', ''),
                        True
                    )
                    return redirect('network:static_routes_list')
                else:
                    messages.error(request, f'Failed to update route: {result.get("error", "Unknown error")}')

            except Exception as e:
                messages.error(request, f'Failed to update static route: {str(e)}')
                log_user_activity(
                    request.user,
                    f'Failed to update static route: {route.destination} - {str(e)}',
                    request.META.get('REMOTE_ADDR', ''),
                    False
                )
    else:
        form = RouteForm(instance=route)

    context = {
        'form': form,
        'route': route,
        'page_title': f'Edit Static Route: {route.destination}'
    }

    return render(request, 'network/add_static_route.html', context)


@login_required
def delete_static_route_view(request, route_id):
    """Delete static route"""
    route = get_object_or_404(Route, id=route_id)

    if request.method == 'POST':
        try:
            # Remove from system
            result = delete_static_route(
                route.destination,
                route.gateway,
                route.interface.name if route.interface else None
            )

            # Remove from persistent config
            if route.interface:
                remove_persistent_route(route.destination, route.interface.name)

            # Delete from database
            route_destination = route.destination
            route.delete()

            if result['success']:
                messages.success(request, f'Static route "{route_destination}" deleted successfully!')
            else:
                messages.warning(request, f'Route deleted from database, but system removal failed: {result.get("error", "Unknown error")}')

            log_user_activity(
                request.user,
                f'Deleted static route: {route_destination}',
                request.META.get('REMOTE_ADDR', ''),
                True
            )

        except Exception as e:
            messages.error(request, f'Failed to delete static route: {str(e)}')
            log_user_activity(
                request.user,
                f'Failed to delete static route: {route.destination} - {str(e)}',
                request.META.get('REMOTE_ADDR', ''),
                False
            )

    return redirect('network:static_routes_list')


@login_required
def network_status_api(request):
    """API endpoint for network status"""
    try:
        status = {
            "forwarding": get_ip_forwarding_status(),
            "nat": get_nat_status(),
            "interfaces": get_network_interfaces(),
            "routes": get_routing_table(),
        }
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
