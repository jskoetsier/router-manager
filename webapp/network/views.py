"""
Network management views
"""
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dashboard.utils import log_user_activity
from .utils import (
    get_ip_forwarding_status, 
    set_ip_forwarding, 
    get_nat_status, 
    configure_basic_nat,
    get_network_interfaces,
    get_routing_table,
    get_nftables_rules
)


@login_required
def home(request):
    """Network management home"""
    # Get current system status
    forwarding_status = get_ip_forwarding_status()
    nat_status = get_nat_status()
    interfaces = get_network_interfaces()
    
    context = {
        'forwarding_status': forwarding_status,
        'nat_status': nat_status,
        'interfaces': interfaces,
        'interface_count': len(interfaces) if 'error' not in interfaces else 0
    }
    return render(request, 'network/home.html', context)


@login_required
def interfaces_list(request):
    """List network interfaces"""
    interfaces = get_network_interfaces()
    context = {
        'interfaces': interfaces
    }
    return render(request, 'network/interfaces_list.html', context)


@login_required
def interface_detail(request, interface_name):
    """Interface configuration details"""
    interfaces = get_network_interfaces()
    interface = interfaces.get(interface_name, {})
    
    context = {
        'interface_name': interface_name,
        'interface': interface
    }
    return render(request, 'network/interface_detail.html', context)


@login_required
def routing_table(request):
    """Network routing table"""
    routes = get_routing_table()
    context = {
        'routes': routes
    }
    return render(request, 'network/routing_table.html', context)


@login_required
def system_settings(request):
    """System network settings"""
    if request.method == 'POST':
        try:
            # Handle IP forwarding toggle
            if 'toggle_ip_forwarding' in request.POST:
                ipv4_enabled = request.POST.get('ipv4_forwarding') == 'on'
                ipv6_enabled = request.POST.get('ipv6_forwarding') == 'on'
                
                results = set_ip_forwarding(ipv4_enabled, ipv6_enabled, permanent=True)
                
                success_count = sum(1 for _, success, _ in results if success)
                total_count = len(results)
                
                if success_count == total_count:
                    messages.success(request, 'IP forwarding settings updated successfully.')
                    log_user_activity(
                        request.user,
                        f'Updated IP forwarding: IPv4={ipv4_enabled}, IPv6={ipv6_enabled}',
                        request.META.get('REMOTE_ADDR', ''),
                        True
                    )
                else:
                    failed_operations = [name for name, success, error in results if not success]
                    messages.warning(request, f'Some operations failed: {", ".join(failed_operations)}')
                    log_user_activity(
                        request.user,
                        f'Partially updated IP forwarding settings',
                        request.META.get('REMOTE_ADDR', ''),
                        False
                    )
            
            # Handle NAT configuration
            elif 'toggle_nat' in request.POST:
                nat_enabled = request.POST.get('nat_enabled') == 'on'
                interface = request.POST.get('nat_interface', 'eth0')
                
                results = configure_basic_nat(interface, nat_enabled)
                
                success_count = sum(1 for _, success, _ in results if success)
                total_count = len(results)
                
                if success_count == total_count:
                    messages.success(request, f'NAT {"enabled" if nat_enabled else "disabled"} successfully.')
                    log_user_activity(
                        request.user,
                        f'{"Enabled" if nat_enabled else "Disabled"} NAT on interface {interface}',
                        request.META.get('REMOTE_ADDR', ''),
                        True
                    )
                else:
                    messages.error(request, 'Failed to configure NAT. Please check system logs.')
                    log_user_activity(
                        request.user,
                        f'Failed to configure NAT',
                        request.META.get('REMOTE_ADDR', ''),
                        False
                    )
        
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            log_user_activity(
                request.user,
                f'Network settings error: {str(e)}',
                request.META.get('REMOTE_ADDR', ''),
                False
            )
        
        return redirect('network:system_settings')
    
    # GET request - show current settings
    forwarding_status = get_ip_forwarding_status()
    nat_status = get_nat_status()
    interfaces = get_network_interfaces()
    nftables_info = get_nftables_rules()
    
    # Calculate interface statistics
    interface_count = 0
    active_interface_count = 0
    if interfaces and 'error' not in interfaces:
        interface_count = len(interfaces)
        active_interface_count = sum(1 for iface in interfaces.values() if iface.get('state') == 'UP')
    
    context = {
        'forwarding_status': forwarding_status,
        'nat_status': nat_status,
        'interfaces': interfaces,
        'nftables_info': nftables_info,
        'interface_count': interface_count,
        'active_interface_count': active_interface_count
    }
    return render(request, 'network/system_settings.html', context)


@login_required
def network_status_api(request):
    """API endpoint for network status"""
    try:
        status = {
            'forwarding': get_ip_forwarding_status(),
            'nat': get_nat_status(),
            'interfaces': get_network_interfaces(),
            'routes': get_routing_table()
        }
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)