"""
Monitoring views
"""

import json
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg, Max, Min
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import (
    MetricData, Alert, AlertInstance, ServiceStatus, 
    NetworkInterface, ConnectionMonitor, SystemLog,
    MonitoringSettings
)
from .forms import AlertForm, MonitoringSettingsForm
from .utils import SystemMonitor


@login_required
def home(request):
    """Enhanced monitoring dashboard home"""
    # Get recent metrics for dashboard widgets
    now = timezone.now()
    hour_ago = now - timedelta(hours=1)
    
    # CPU usage
    latest_cpu = MetricData.objects.filter(
        metric_type='cpu',
        source='system'
    ).first()
    
    # Memory usage
    latest_memory = MetricData.objects.filter(
        metric_type='memory',
        source='system'
    ).first()
    
    # Disk usage (average across all disks)
    disk_metrics = MetricData.objects.filter(
        metric_type='disk',
        timestamp__gte=hour_ago
    ).values('source').annotate(
        latest_value=Max('value')
    )
    
    # Network throughput (last hour)
    network_metrics = MetricData.objects.filter(
        metric_type__in=['network_rx_bytes', 'network_tx_bytes'],
        timestamp__gte=hour_ago
    ).exclude(source='lo')
    
    # Active alerts
    active_alerts = AlertInstance.objects.filter(
        resolved_at__isnull=True
    ).order_by('-triggered_at')[:5]
    
    # Service status
    services = ServiceStatus.objects.all()
    
    # Network interfaces
    interfaces = NetworkInterface.objects.filter(monitor_enabled=True)
    
    # Recent system logs
    recent_logs = SystemLog.objects.filter(
        timestamp__gte=now - timedelta(hours=6)
    ).order_by('-timestamp')[:10]
    
    context = {
        'latest_cpu': latest_cpu,
        'latest_memory': latest_memory,
        'disk_metrics': disk_metrics,
        'network_metrics': network_metrics,
        'active_alerts': active_alerts,
        'services': services,
        'interfaces': interfaces,
        'recent_logs': recent_logs,
    }
    
    return render(request, "monitoring/home.html", context)


@login_required
def metrics_view(request):
    """Advanced system metrics with historical charts"""
    # Get time range parameters
    hours = request.GET.get('hours', '24')
    metric_type = request.GET.get('type', 'cpu')
    source = request.GET.get('source', '')
    
    try:
        hours = int(hours)
    except ValueError:
        hours = 24
    
    # Calculate time range
    end_time = timezone.now()
    start_time = end_time - timedelta(hours=hours)
    
    # Get available metric types and sources
    available_metrics = MetricData.METRIC_TYPES
    
    # Get available sources for selected metric type
    available_sources = MetricData.objects.filter(
        metric_type=metric_type
    ).values_list('source', flat=True).distinct()
    
    # Get historical data
    metrics_query = MetricData.objects.filter(
        metric_type=metric_type,
        timestamp__gte=start_time
    ).order_by('timestamp')
    
    if source:
        metrics_query = metrics_query.filter(source=source)
    
    # Aggregate data for performance (group by time intervals)
    if hours <= 6:
        # 5-minute intervals for last 6 hours
        interval_minutes = 5
    elif hours <= 24:
        # 15-minute intervals for last 24 hours
        interval_minutes = 15
    else:
        # 1-hour intervals for longer periods
        interval_minutes = 60
    
    # Prepare chart data
    chart_data = []
    current_time = start_time
    
    while current_time <= end_time:
        interval_end = current_time + timedelta(minutes=interval_minutes)
        
        interval_metrics = metrics_query.filter(
            timestamp__gte=current_time,
            timestamp__lt=interval_end
        )
        
        if interval_metrics.exists():
            avg_value = interval_metrics.aggregate(Avg('value'))['value__avg']
            chart_data.append({
                'timestamp': current_time.isoformat(),
                'value': round(avg_value, 2) if avg_value else 0
            })
        
        current_time = interval_end
    
    # Get current stats
    latest_metric = metrics_query.last()
    stats = metrics_query.aggregate(
        avg=Avg('value'),
        min=Min('value'),
        max=Max('value')
    )
    
    context = {
        'metric_type': metric_type,
        'source': source,
        'hours': hours,
        'available_metrics': available_metrics,
        'available_sources': available_sources,
        'chart_data': json.dumps(chart_data),
        'latest_metric': latest_metric,
        'stats': stats,
        'interval_minutes': interval_minutes,
    }
    
    return render(request, "monitoring/metrics.html", context)


@login_required
def alerts_list(request):
    """Enhanced alerts management"""
    # Get filter parameters
    status = request.GET.get('status', 'all')
    severity = request.GET.get('severity', 'all')
    alert_type = request.GET.get('type', 'all')
    
    # Build query
    alerts_query = Alert.objects.all()
    
    if status == 'active':
        alerts_query = alerts_query.filter(enabled=True)
    elif status == 'inactive':
        alerts_query = alerts_query.filter(enabled=False)
    
    if severity != 'all':
        alerts_query = alerts_query.filter(severity=severity)
        
    if alert_type != 'all':
        alerts_query = alerts_query.filter(alert_type=alert_type)
    
    alerts = alerts_query.order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    alerts_page = paginator.get_page(page_number)
    
    # Get recent alert instances
    recent_instances = AlertInstance.objects.select_related('alert').order_by('-triggered_at')[:10]
    
    # Get stats
    alert_stats = {
        'total': Alert.objects.count(),
        'active': Alert.objects.filter(enabled=True).count(),
        'critical': AlertInstance.objects.filter(
            triggered_at__gte=timezone.now() - timedelta(days=1),
            alert__severity='critical'
        ).count(),
        'recent_triggers': AlertInstance.objects.filter(
            triggered_at__gte=timezone.now() - timedelta(hours=24)
        ).count(),
    }
    
    context = {
        'alerts': alerts_page,
        'recent_instances': recent_instances,
        'alert_stats': alert_stats,
        'status_filter': status,
        'severity_filter': severity,
        'type_filter': alert_type,
        'severities': Alert.SEVERITY_LEVELS,
        'alert_types': Alert.ALERT_TYPES,
    }
    
    return render(request, "monitoring/alerts_list.html", context)


@login_required
def alert_create(request):
    """Create new alert"""
    if request.method == 'POST':
        form = AlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.created_by = request.user
            alert.save()
            messages.success(request, f'Alert "{alert.name}" created successfully.')
            return redirect('monitoring:alerts_list')
    else:
        form = AlertForm()
    
    return render(request, 'monitoring/alert_form.html', {
        'form': form,
        'title': 'Create Alert'
    })


@login_required
def alert_edit(request, alert_id):
    """Edit existing alert"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    if request.method == 'POST':
        form = AlertForm(request.POST, instance=alert)
        if form.is_valid():
            form.save()
            messages.success(request, f'Alert "{alert.name}" updated successfully.')
            return redirect('monitoring:alerts_list')
    else:
        form = AlertForm(instance=alert)
    
    return render(request, 'monitoring/alert_form.html', {
        'form': form,
        'alert': alert,
        'title': 'Edit Alert'
    })


@login_required
@require_http_methods(["POST"])
def alert_toggle(request, alert_id):
    """Toggle alert enabled/disabled status"""
    alert = get_object_or_404(Alert, id=alert_id)
    alert.enabled = not alert.enabled
    alert.save()
    
    status = "enabled" if alert.enabled else "disabled"
    messages.success(request, f'Alert "{alert.name}" {status}.')
    
    return redirect('monitoring:alerts_list')


@login_required
def services_status(request):
    """Enhanced system services status"""
    services = ServiceStatus.objects.all().order_by('service_name')
    
    # Get service stats
    service_stats = {
        'total': services.count(),
        'running': services.filter(status='running').count(),
        'stopped': services.filter(status='stopped').count(),
        'failed': services.filter(status='failed').count(),
    }
    
    # Get resource usage data for running services
    resource_data = []
    for service in services.filter(status='running'):
        if service.cpu_percent > 0 or service.memory_mb > 0:
            resource_data.append({
                'name': service.display_name or service.service_name,
                'cpu': service.cpu_percent,
                'memory': service.memory_mb
            })
    
    context = {
        'services': services,
        'service_stats': service_stats,
        'resource_data': json.dumps(resource_data),
    }
    
    return render(request, "monitoring/services_status.html", context)


@login_required
def network_interfaces(request):
    """Network interfaces monitoring"""
    interfaces = NetworkInterface.objects.all().order_by('interface_name')
    
    # Get recent network metrics for each interface
    for interface in interfaces:
        # Get latest metrics
        latest_rx = MetricData.objects.filter(
            metric_type='network_rx_bytes',
            source=interface.interface_name
        ).first()
        
        latest_tx = MetricData.objects.filter(
            metric_type='network_tx_bytes',
            source=interface.interface_name
        ).first()
        
        # Calculate throughput (last hour average)
        hour_ago = timezone.now() - timedelta(hours=1)
        recent_metrics = MetricData.objects.filter(
            metric_type__in=['network_rx_bytes', 'network_tx_bytes'],
            source=interface.interface_name,
            timestamp__gte=hour_ago
        )
        
        interface.latest_rx = latest_rx
        interface.latest_tx = latest_tx
        interface.recent_activity = recent_metrics.exists()
    
    context = {
        'interfaces': interfaces,
    }
    
    return render(request, "monitoring/network_interfaces.html", context)


@login_required
def connections_monitor(request):
    """Active network connections monitoring"""
    # Get filter parameters
    protocol = request.GET.get('protocol', 'all')
    state = request.GET.get('state', 'all')
    
    # Build query
    connections_query = ConnectionMonitor.objects.all()
    
    if protocol != 'all':
        connections_query = connections_query.filter(protocol=protocol)
        
    if state != 'all':
        connections_query = connections_query.filter(state=state)
    
    connections = connections_query.order_by('-timestamp')
    
    # Paginate results
    paginator = Paginator(connections, 50)
    page_number = request.GET.get('page')
    connections_page = paginator.get_page(page_number)
    
    # Get connection stats
    connection_stats = ConnectionMonitor.objects.aggregate(
        total=Count('id'),
        tcp_count=Count('id', filter=Q(protocol='tcp')),
        udp_count=Count('id', filter=Q(protocol='udp')),
        established_count=Count('id', filter=Q(state='ESTABLISHED')),
    )
    
    # Get available protocols and states
    available_protocols = ConnectionMonitor.objects.values_list('protocol', flat=True).distinct()
    available_states = ConnectionMonitor.objects.values_list('state', flat=True).distinct()
    
    context = {
        'connections': connections_page,
        'connection_stats': connection_stats,
        'available_protocols': available_protocols,
        'available_states': available_states,
        'protocol_filter': protocol,
        'state_filter': state,
    }
    
    return render(request, "monitoring/connections.html", context)


@login_required
def logs_view(request):
    """System logs aggregation and viewing"""
    # Get filter parameters
    source = request.GET.get('source', 'all')
    level = request.GET.get('level', 'all')
    hours = request.GET.get('hours', '24')
    search = request.GET.get('search', '')
    
    try:
        hours = int(hours)
    except ValueError:
        hours = 24
    
    # Calculate time range
    time_filter = timezone.now() - timedelta(hours=hours)
    
    # Build query
    logs_query = SystemLog.objects.filter(timestamp__gte=time_filter)
    
    if source != 'all':
        logs_query = logs_query.filter(source=source)
        
    if level != 'all':
        logs_query = logs_query.filter(level=level)
        
    if search:
        logs_query = logs_query.filter(
            Q(message__icontains=search) | 
            Q(process__icontains=search) |
            Q(hostname__icontains=search)
        )
    
    logs = logs_query.order_by('-timestamp')
    
    # Paginate results
    paginator = Paginator(logs, 100)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)
    
    # Get log statistics
    log_stats = SystemLog.objects.filter(timestamp__gte=time_filter).aggregate(
        total=Count('id'),
        error_count=Count('id', filter=Q(level='ERROR')),
        warning_count=Count('id', filter=Q(level='WARNING')),
        info_count=Count('id', filter=Q(level='INFO')),
    )
    
    # Get available sources and levels
    available_sources = SystemLog.objects.values_list('source', flat=True).distinct()
    available_levels = [level[0] for level in SystemLog.LOG_LEVELS]
    
    context = {
        'logs': logs_page,
        'log_stats': log_stats,
        'available_sources': available_sources,
        'available_levels': available_levels,
        'source_filter': source,
        'level_filter': level,
        'hours_filter': hours,
        'search_query': search,
    }
    
    return render(request, "monitoring/logs.html", context)


@login_required
def settings_view(request):
    """Monitoring settings configuration"""
    settings_obj = MonitoringSettings.get_settings()
    
    if request.method == 'POST':
        form = MonitoringSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Monitoring settings updated successfully.')
            return redirect('monitoring:settings')
    else:
        form = MonitoringSettingsForm(instance=settings_obj)
    
    context = {
        'form': form,
        'settings': settings_obj,
    }
    
    return render(request, "monitoring/settings.html", context)


# API endpoints for real-time data

@login_required
def api_metrics_data(request):
    """API endpoint for real-time metrics data"""
    metric_type = request.GET.get('type', 'cpu')
    source = request.GET.get('source', '')
    minutes = int(request.GET.get('minutes', '60'))
    
    time_filter = timezone.now() - timedelta(minutes=minutes)
    
    query = MetricData.objects.filter(
        metric_type=metric_type,
        timestamp__gte=time_filter
    ).order_by('timestamp')
    
    if source:
        query = query.filter(source=source)
    
    data = [{
        'timestamp': metric.timestamp.isoformat(),
        'value': metric.value,
        'source': metric.source,
        'unit': metric.unit
    } for metric in query[:200]]  # Limit to prevent large responses
    
    return JsonResponse({'data': data})


@login_required
def api_system_status(request):
    """API endpoint for system status summary"""
    # Get latest metrics
    latest_cpu = MetricData.objects.filter(metric_type='cpu', source='system').first()
    latest_memory = MetricData.objects.filter(metric_type='memory', source='system').first()
    
    # Get service counts
    services = ServiceStatus.objects.aggregate(
        total=Count('id'),
        running=Count('id', filter=Q(status='running')),
        failed=Count('id', filter=Q(status='failed'))
    )
    
    # Get active alerts
    active_alerts = AlertInstance.objects.filter(resolved_at__isnull=True).count()
    
    data = {
        'cpu_usage': latest_cpu.value if latest_cpu else 0,
        'memory_usage': latest_memory.value if latest_memory else 0,
        'services_running': services['running'],
        'services_failed': services['failed'],
        'active_alerts': active_alerts,
        'timestamp': timezone.now().isoformat()
    }
    
    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])
def force_metrics_collection(request):
    """Force immediate metrics collection"""
    try:
        monitor = SystemMonitor()
        monitor.collect_all_metrics()
        messages.success(request, 'Metrics collection triggered successfully.')
    except Exception as e:
        messages.error(request, f'Error triggering metrics collection: {e}')
    
    return redirect(request.META.get('HTTP_REFERER', 'monitoring:home'))
