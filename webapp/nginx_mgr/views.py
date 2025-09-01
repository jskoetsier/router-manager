from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
import logging

from .models import NginxProxyConfig, SSLCertificate, NginxDeploymentLog
from .forms import NginxProxyConfigForm, QuickProxyForm
from .utils import NginxManager, CertbotManager

logger = logging.getLogger(__name__)


@login_required
@staff_member_required
def nginx_list(request):
    """List all nginx proxy configurations"""
    configs = NginxProxyConfig.objects.all()

    # Filter by status if requested
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        configs = configs.filter(is_active=True)
    elif status_filter == 'deployed':
        configs = configs.filter(is_deployed=True)
    elif status_filter == 'ssl':
        configs = configs.filter(ssl_enabled=True)

    # Search by name or domain
    search = request.GET.get('search', '')
    if search:
        from django.db import models
        configs = configs.filter(
            models.Q(name__icontains=search) |
            models.Q(domain_name__icontains=search)
        )

    # Pagination
    paginator = Paginator(configs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search': search,
        'total_configs': NginxProxyConfig.objects.count(),
        'active_configs': NginxProxyConfig.objects.filter(is_active=True).count(),
        'deployed_configs': NginxProxyConfig.objects.filter(is_deployed=True).count(),
        'ssl_configs': NginxProxyConfig.objects.filter(ssl_enabled=True).count(),
    }

    return render(request, 'nginx_mgr/list.html', context)


@login_required
@staff_member_required
def nginx_create(request):
    """Create a new nginx proxy configuration"""
    if request.method == 'POST':
        form = NginxProxyConfigForm(request.POST)
        if form.is_valid():
            try:
                config = form.save()
                messages.success(request, f'Nginx configuration "{config.name}" created successfully!')
                return redirect('nginx_mgr:detail', pk=config.pk)
            except Exception as e:
                logger.error(f"Error creating nginx config: {e}")
                messages.error(request, f'Error creating configuration: {e}')
    else:
        form = NginxProxyConfigForm()

    return render(request, 'nginx_mgr/create.html', {'form': form})


@login_required
@staff_member_required
def nginx_quick_create(request):
    """Quick create form for simple proxy configurations"""
    if request.method == 'POST':
        form = QuickProxyForm(request.POST)
        if form.is_valid():
            try:
                config = form.create_proxy_config()
                if config:
                    config.save()
                    messages.success(request, f'Quick proxy configuration "{config.name}" created successfully!')
                    return redirect('nginx_mgr:detail', pk=config.pk)
                else:
                    messages.error(request, 'Error creating configuration from form data')
            except Exception as e:
                logger.error(f"Error creating quick nginx config: {e}")
                messages.error(request, f'Error creating configuration: {e}')
    else:
        form = QuickProxyForm()

    return render(request, 'nginx_mgr/quick_create.html', {'form': form})


@login_required
@staff_member_required
def nginx_detail(request, pk):
    """View details of a nginx proxy configuration"""
    config = get_object_or_404(NginxProxyConfig, pk=pk)

    # Get SSL certificate info if exists
    ssl_cert = getattr(config, 'ssl_certificate', None)

    # Get deployment logs
    deployment_logs = config.deployment_logs.order_by('-started_at')[:10]

    # Get nginx manager status
    nginx_manager = NginxManager()
    nginx_status = nginx_manager.get_status()

    context = {
        'config': config,
        'ssl_cert': ssl_cert,
        'deployment_logs': deployment_logs,
        'nginx_status': nginx_status,
    }

    return render(request, 'nginx_mgr/detail.html', context)


@login_required
@staff_member_required
def nginx_edit(request, pk):
    """Edit an existing nginx proxy configuration"""
    config = get_object_or_404(NginxProxyConfig, pk=pk)

    if request.method == 'POST':
        form = NginxProxyConfigForm(request.POST, instance=config)
        if form.is_valid():
            try:
                updated_config = form.save()
                messages.success(request, f'Configuration "{updated_config.name}" updated successfully!')
                return redirect('nginx_mgr:detail', pk=updated_config.pk)
            except Exception as e:
                logger.error(f"Error updating nginx config {pk}: {e}")
                messages.error(request, f'Error updating configuration: {e}')
    else:
        form = NginxProxyConfigForm(instance=config)

    context = {
        'form': form,
        'config': config,
    }

    return render(request, 'nginx_mgr/edit.html', context)


@login_required
@staff_member_required
@require_POST
def nginx_delete(request, pk):
    """Delete a nginx proxy configuration"""
    config = get_object_or_404(NginxProxyConfig, pk=pk)

    try:
        # If config is deployed, remove from nginx first
        if config.is_deployed:
            nginx_manager = NginxManager()
            nginx_manager.remove_config(config)

        config_name = config.name
        config.delete()

        messages.success(request, f'Configuration "{config_name}" deleted successfully!')

    except Exception as e:
        logger.error(f"Error deleting nginx config {pk}: {e}")
        messages.error(request, f'Error deleting configuration: {e}')

    return redirect('nginx_mgr:list')


@login_required
@staff_member_required
@require_POST
def nginx_deploy(request, pk):
    """Deploy a nginx proxy configuration"""
    config = get_object_or_404(NginxProxyConfig, pk=pk)

    log = None
    try:
        with transaction.atomic():
            # Create deployment log
            log = NginxDeploymentLog.objects.create(
                proxy_config=config,
                action='deploy' if not config.is_deployed else 'update',
                status='in_progress',
                config_snapshot=_create_config_snapshot(config)
            )

            nginx_manager = NginxManager()

            # Deploy configuration
            success, message = nginx_manager.deploy_config(config)

            if success:
                # If SSL is enabled and auto_ssl is true, get SSL certificate
                if config.ssl_enabled and config.auto_ssl:
                    certbot_manager = CertbotManager()
                    cert_success, cert_message = certbot_manager.obtain_certificate(config)

                    if not cert_success:
                        log.mark_completed('failed', f'Config deployed but SSL failed: {cert_message}')
                        messages.warning(request, f'Configuration deployed but SSL certificate failed: {cert_message}')
                        return redirect('nginx_mgr:detail', pk=pk)

                # Mark as deployed
                config.mark_deployed()
                log.mark_completed('success', message)
                messages.success(request, f'Configuration "{config.name}" deployed successfully!')
            else:
                log.mark_completed('failed', message)
                messages.error(request, f'Deployment failed: {message}')

    except Exception as e:
        logger.error(f"Error deploying nginx config {pk}: {e}")
        if log:
            log.mark_completed('failed', str(e))
        messages.error(request, f'Deployment error: {e}')

    return redirect('nginx_mgr:detail', pk=pk)


@login_required
@staff_member_required
@require_POST
def nginx_undeploy(request, pk):
    """Remove a nginx proxy configuration from deployment"""
    config = get_object_or_404(NginxProxyConfig, pk=pk)

    log = None
    try:
        with transaction.atomic():
            # Create deployment log
            log = NginxDeploymentLog.objects.create(
                proxy_config=config,
                action='remove',
                status='in_progress',
                config_snapshot=_create_config_snapshot(config)
            )

            nginx_manager = NginxManager()
            success, message = nginx_manager.remove_config(config)

            if success:
                config.is_deployed = False
                config.deployed_at = None
                config.save()

                log.mark_completed('success', message)
                messages.success(request, f'Configuration "{config.name}" removed from deployment!')
            else:
                log.mark_completed('failed', message)
                messages.error(request, f'Removal failed: {message}')

    except Exception as e:
        logger.error(f"Error removing nginx config {pk}: {e}")
        if log:
            log.mark_completed('failed', str(e))
        messages.error(request, f'Removal error: {e}')

    return redirect('nginx_mgr:detail', pk=pk)


@login_required
@staff_member_required
@require_POST
def ssl_renew(request, pk):
    """Renew SSL certificate for a configuration"""
    config = get_object_or_404(NginxProxyConfig, pk=pk)

    if not config.ssl_enabled or not config.auto_ssl:
        messages.error(request, 'SSL is not enabled or auto-SSL is disabled for this configuration')
        return redirect('nginx_mgr:detail', pk=pk)

    log = None
    try:
        with transaction.atomic():
            # Create deployment log
            log = NginxDeploymentLog.objects.create(
                proxy_config=config,
                action='ssl_renew',
                status='in_progress',
                config_snapshot=_create_config_snapshot(config)
            )

            certbot_manager = CertbotManager()
            success, message = certbot_manager.renew_certificate(config)

            if success:
                log.mark_completed('success', message)
                messages.success(request, f'SSL certificate renewed for "{config.name}"!')

                # Reload nginx to use new certificate
                nginx_manager = NginxManager()
                nginx_manager.reload()
            else:
                log.mark_completed('failed', message)
                messages.error(request, f'SSL renewal failed: {message}')

    except Exception as e:
        logger.error(f"Error renewing SSL for config {pk}: {e}")
        if log:
            log.mark_completed('failed', str(e))
        messages.error(request, f'SSL renewal error: {e}')

    return redirect('nginx_mgr:detail', pk=pk)


@login_required
@staff_member_required
def nginx_status(request):
    """Get nginx status and system information"""
    nginx_manager = NginxManager()
    certbot_manager = CertbotManager()

    context = {
        'nginx_status': nginx_manager.get_status(),
        'nginx_version': nginx_manager.get_version(),
        'certbot_status': certbot_manager.get_status(),
        'active_configs': NginxProxyConfig.objects.filter(is_active=True).count(),
        'deployed_configs': NginxProxyConfig.objects.filter(is_deployed=True).count(),
        'expiring_certs': _get_expiring_certificates(),
    }

    return render(request, 'nginx_mgr/status.html', context)


@login_required
@staff_member_required
def deployment_logs(request):
    """View all deployment logs"""
    logs = NginxDeploymentLog.objects.select_related('proxy_config').order_by('-started_at')

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        logs = logs.filter(status=status_filter)

    # Filter by action
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)

    # Pagination
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'action_filter': action_filter,
    }

    return render(request, 'nginx_mgr/logs.html', context)


@login_required
@staff_member_required
def ajax_config_status(request, pk):
    """AJAX endpoint to get configuration status"""
    try:
        config = get_object_or_404(NginxProxyConfig, pk=pk)
        nginx_manager = NginxManager()

        data = {
            'is_deployed': config.is_deployed,
            'nginx_running': nginx_manager.is_running(),
            'config_valid': nginx_manager.test_config(),
            'ssl_cert_exists': hasattr(config, 'ssl_certificate'),
        }

        if hasattr(config, 'ssl_certificate'):
            ssl_cert = config.ssl_certificate
            data['ssl_expiry'] = ssl_cert.expiry_date.isoformat()
            data['ssl_expiring_soon'] = ssl_cert.is_expiring_soon()

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def _create_config_snapshot(config):
    """Create a snapshot of the configuration for logging"""
    return {
        'name': config.name,
        'domain_name': config.domain_name,
        'upstream_url': config.get_upstream_url(),
        'ssl_enabled': config.ssl_enabled,
        'is_active': config.is_active,
        'timestamp': timezone.now().isoformat(),
    }


def _get_expiring_certificates():
    """Get list of certificates expiring within 30 days"""
    expiring_certs = []

    for cert in SSLCertificate.objects.filter(is_valid=True):
        if cert.is_expiring_soon(30):
            expiring_certs.append({
                'domain': cert.proxy_config.domain_name,
                'expires': cert.expiry_date,
                'days_left': (cert.expiry_date - timezone.now()).days,
                'config_id': cert.proxy_config.id,
            })

    return expiring_certs
