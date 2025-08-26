"""
VPN management views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from dashboard.utils import log_user_activity
from .models import VPNTunnel
from .forms import VPNTunnelForm, QuickVPNForm
from .utils import (
    get_strongswan_status, 
    create_ipsec_config, 
    add_tunnel_to_strongswan,
    remove_tunnel_from_strongswan,
    get_tunnel_status
)


@login_required
def home(request):
    """VPN management home"""
    # Get StrongSwan status
    strongswan_status = get_strongswan_status()
    
    # Get tunnel counts
    total_tunnels = VPNTunnel.objects.count()
    active_tunnels = VPNTunnel.objects.filter(enabled=True).count()
    
    # Get recent tunnels
    recent_tunnels = VPNTunnel.objects.order_by('-created_at')[:5]
    
    context = {
        'strongswan_status': strongswan_status,
        'total_tunnels': total_tunnels,
        'active_tunnels': active_tunnels,
        'recent_tunnels': recent_tunnels,
    }
    
    return render(request, 'vpn/home.html', context)


@login_required
def tunnels_list(request):
    """List VPN tunnels"""
    tunnels = VPNTunnel.objects.all().order_by('name')
    
    # Add status information to each tunnel
    for tunnel in tunnels:
        tunnel.current_status = get_tunnel_status(tunnel.name)
    
    # Pagination
    paginator = Paginator(tunnels, 10)
    page_number = request.GET.get('page')
    tunnels_page = paginator.get_page(page_number)
    
    context = {
        'tunnels': tunnels_page,
    }
    
    return render(request, 'vpn/tunnels_list.html', context)


@login_required
def add_tunnel(request):
    """Add new VPN tunnel"""
    if request.method == 'POST':
        form = VPNTunnelForm(request.POST)
        if form.is_valid():
            try:
                # Create the tunnel object
                tunnel = form.save(commit=False)
                tunnel.created_by = request.user
                tunnel.save()
                
                # Create StrongSwan configuration
                config = create_ipsec_config(
                    tunnel_name=tunnel.name,
                    local_ip=tunnel.local_ip,
                    remote_ip=tunnel.remote_ip,
                    local_subnet=tunnel.local_subnet,
                    remote_subnet=tunnel.remote_subnet,
                    psk=tunnel.pre_shared_key
                )
                
                if config['success']:
                    # Add configuration to StrongSwan
                    config['name'] = tunnel.name
                    results = add_tunnel_to_strongswan(config)
                    
                    # Check if all operations succeeded
                    success_count = sum(1 for _, success, _ in results if success)
                    total_count = len(results)
                    
                    if success_count == total_count:
                        messages.success(request, f'VPN tunnel "{tunnel.name}" created successfully!')
                        log_user_activity(
                            request.user,
                            f'Created VPN tunnel: {tunnel.name}',
                            request.META.get('REMOTE_ADDR', ''),
                            True
                        )
                        return redirect('vpn:tunnels_list')
                    else:
                        # Some operations failed
                        failed_operations = [name for name, success, error in results if not success]
                        messages.warning(request, f'Tunnel created but some configuration failed: {", ".join(failed_operations)}')
                        log_user_activity(
                            request.user,
                            f'Partially created VPN tunnel: {tunnel.name}',
                            request.META.get('REMOTE_ADDR', ''),
                            False
                        )
                else:
                    messages.error(request, f'Failed to create tunnel configuration: {config.get("error", "Unknown error")}')
                    tunnel.delete()  # Clean up the database entry
                    
            except Exception as e:
                messages.error(request, f'Failed to create VPN tunnel: {str(e)}')
                log_user_activity(
                    request.user,
                    f'Failed to create VPN tunnel: {str(e)}',
                    request.META.get('REMOTE_ADDR', ''),
                    False
                )
    else:
        form = VPNTunnelForm()
    
    context = {
        'form': form,
        'page_title': 'Add VPN Tunnel'
    }
    
    return render(request, 'vpn/add_tunnel.html', context)


@login_required
def edit_tunnel(request, tunnel_id):
    """Edit existing VPN tunnel"""
    tunnel = get_object_or_404(VPNTunnel, id=tunnel_id)
    
    if request.method == 'POST':
        form = VPNTunnelForm(request.POST, instance=tunnel)
        if form.is_valid():
            form.save()
            messages.success(request, f'VPN tunnel "{tunnel.name}" updated successfully!')
            log_user_activity(
                request.user,
                f'Updated VPN tunnel: {tunnel.name}',
                request.META.get('REMOTE_ADDR', ''),
                True
            )
            return redirect('vpn:tunnels_list')
    else:
        form = VPNTunnelForm(instance=tunnel)
    
    context = {
        'form': form,
        'tunnel': tunnel,
        'page_title': f'Edit VPN Tunnel: {tunnel.name}'
    }
    
    return render(request, 'vpn/add_tunnel.html', context)


@login_required
def delete_tunnel(request, tunnel_id):
    """Delete VPN tunnel"""
    tunnel = get_object_or_404(VPNTunnel, id=tunnel_id)
    
    if request.method == 'POST':
        try:
            # Remove from StrongSwan configuration
            results = remove_tunnel_from_strongswan(tunnel.name)
            
            # Delete from database
            tunnel_name = tunnel.name
            tunnel.delete()
            
            messages.success(request, f'VPN tunnel "{tunnel_name}" deleted successfully!')
            log_user_activity(
                request.user,
                f'Deleted VPN tunnel: {tunnel_name}',
                request.META.get('REMOTE_ADDR', ''),
                True
            )
            
        except Exception as e:
            messages.error(request, f'Failed to delete VPN tunnel: {str(e)}')
            log_user_activity(
                request.user,
                f'Failed to delete VPN tunnel: {tunnel.name} - {str(e)}',
                request.META.get('REMOTE_ADDR', ''),
                False
            )
    
    return redirect('vpn:tunnels_list')


@login_required
def tunnel_control(request, tunnel_id, action):
    """Control tunnel (start/stop/restart)"""
    tunnel = get_object_or_404(VPNTunnel, id=tunnel_id)
    
    try:
        if action == 'start':
            result = add_tunnel_to_strongswan({'name': tunnel.name})
            message = f'Started VPN tunnel "{tunnel.name}"'
        elif action == 'stop':
            result = remove_tunnel_from_strongswan(tunnel.name)
            message = f'Stopped VPN tunnel "{tunnel.name}"'
        elif action == 'restart':
            # Stop then start
            remove_tunnel_from_strongswan(tunnel.name)
            result = add_tunnel_to_strongswan({'name': tunnel.name})
            message = f'Restarted VPN tunnel "{tunnel.name}"'
        else:
            messages.error(request, 'Invalid action')
            return redirect('vpn:tunnels_list')
        
        messages.success(request, message)
        log_user_activity(
            request.user,
            f'{action.title()} VPN tunnel: {tunnel.name}',
            request.META.get('REMOTE_ADDR', ''),
            True
        )
        
    except Exception as e:
        messages.error(request, f'Failed to {action} tunnel: {str(e)}')
        log_user_activity(
            request.user,
            f'Failed to {action} VPN tunnel: {tunnel.name} - {str(e)}',
            request.META.get('REMOTE_ADDR', ''),
            False
        )
    
    return redirect('vpn:tunnels_list')


@login_required
def tunnel_status_api(request, tunnel_id):
    """API endpoint for tunnel status"""
    tunnel = get_object_or_404(VPNTunnel, id=tunnel_id)
    
    try:
        status = get_tunnel_status(tunnel.name)
        return JsonResponse({
            'status': status,
            'tunnel_name': tunnel.name
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def certificates_list(request):
    """List VPN certificates"""
    context = {
        'page_title': 'VPN Certificates'
    }
    return render(request, 'vpn/certificates_list.html', context)


@login_required
def users_list(request):
    """List VPN users"""
    context = {
        'page_title': 'VPN Users'
    }
    return render(request, 'vpn/users_list.html', context)


@login_required
def quick_setup(request):
    """Quick VPN setup wizard"""
    if request.method == 'POST':
        form = QuickVPNForm(request.POST)
        if form.is_valid():
            try:
                # Create tunnel with default settings
                tunnel = VPNTunnel.objects.create(
                    name=form.cleaned_data['tunnel_name'],
                    tunnel_type='site-to-site',
                    local_ip='192.168.1.253',  # Default local IP
                    remote_ip=form.cleaned_data['remote_ip'],
                    local_subnet='192.168.1.0/24',  # Default local subnet
                    remote_subnet=form.cleaned_data['remote_subnet'],
                    pre_shared_key='auto-generated-key',  # Will be generated
                    created_by=request.user
                )
                
                messages.success(request, f'Quick VPN setup completed for "{tunnel.name}"!')
                return redirect('vpn:tunnels_list')
                
            except Exception as e:
                messages.error(request, f'Quick setup failed: {str(e)}')
    else:
        form = QuickVPNForm()
    
    context = {
        'form': form,
        'page_title': 'Quick VPN Setup'
    }
    
    return render(request, 'vpn/quick_setup.html', context)