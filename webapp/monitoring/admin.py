"""
Admin interface for monitoring models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    MetricData, Alert, AlertInstance, ServiceStatus,
    NetworkInterface, ConnectionMonitor, SystemLog, MonitoringSettings
)


@admin.register(MetricData)
class MetricDataAdmin(admin.ModelAdmin):
    list_display = ['metric_type', 'value', 'unit', 'source', 'timestamp']
    list_filter = ['metric_type', 'source', 'timestamp']
    search_fields = ['metric_type', 'source']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        # Limit to recent data to avoid performance issues
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        qs = super().get_queryset(request)
        cutoff = timezone.now() - timedelta(days=7)
        return qs.filter(timestamp__gte=cutoff)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'metric_type', 'severity', 'enabled', 
        'threshold_display', 'last_triggered', 'created_by'
    ]
    list_filter = ['severity', 'alert_type', 'enabled', 'metric_type']
    search_fields = ['name', 'metric_type']
    readonly_fields = ['created_at', 'last_checked', 'last_triggered']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'alert_type', 'severity', 'enabled')
        }),
        ('Condition', {
            'fields': ('metric_type', 'comparison_operator', 'threshold_value', 'source')
        }),
        ('Notifications', {
            'fields': ('notification_enabled', 'email_recipients', 'check_interval')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'last_checked', 'last_triggered'),
            'classes': ('collapse',)
        })
    )
    
    def threshold_display(self, obj):
        return f"{obj.comparison_operator} {obj.threshold_value}"
    threshold_display.short_description = "Threshold"
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class AlertInstanceInline(admin.TabularInline):
    model = AlertInstance
    extra = 0
    readonly_fields = ['triggered_at', 'resolved_at', 'value_at_trigger', 'notification_sent']
    fields = ['triggered_at', 'resolved_at', 'value_at_trigger', 'acknowledged', 'notification_sent']


@admin.register(AlertInstance)
class AlertInstanceAdmin(admin.ModelAdmin):
    list_display = [
        'alert', 'severity_display', 'triggered_at', 'resolved_at',
        'value_at_trigger', 'acknowledged', 'notification_sent'
    ]
    list_filter = ['alert__severity', 'acknowledged', 'notification_sent', 'triggered_at']
    search_fields = ['alert__name', 'message']
    date_hierarchy = 'triggered_at'
    readonly_fields = ['triggered_at', 'notification_sent']
    
    def severity_display(self, obj):
        colors = {
            'info': '#17a2b8',
            'warning': '#ffc107', 
            'error': '#fd7e14',
            'critical': '#dc3545'
        }
        color = colors.get(obj.alert.severity, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.alert.severity.upper()
        )
    severity_display.short_description = "Severity"


@admin.register(ServiceStatus)
class ServiceStatusAdmin(admin.ModelAdmin):
    list_display = [
        'service_name', 'display_name', 'status_display', 
        'uptime_display', 'cpu_percent', 'memory_mb', 'last_checked'
    ]
    list_filter = ['status', 'last_checked']
    search_fields = ['service_name', 'display_name']
    readonly_fields = ['last_checked']
    
    def status_display(self, obj):
        colors = {
            'running': '#28a745',
            'stopped': '#ffc107',
            'failed': '#dc3545',
            'unknown': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.upper()
        )
    status_display.short_description = "Status"
    
    def uptime_display(self, obj):
        if obj.uptime_seconds > 0:
            hours = obj.uptime_seconds // 3600
            minutes = (obj.uptime_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return "N/A"
    uptime_display.short_description = "Uptime"


@admin.register(NetworkInterface)
class NetworkInterfaceAdmin(admin.ModelAdmin):
    list_display = [
        'interface_name', 'display_name', 'ip_address', 
        'is_active', 'speed_mbps', 'monitor_enabled', 'last_updated'
    ]
    list_filter = ['is_active', 'monitor_enabled', 'last_updated']
    search_fields = ['interface_name', 'display_name', 'ip_address', 'mac_address']
    readonly_fields = ['last_updated']


@admin.register(ConnectionMonitor)
class ConnectionMonitorAdmin(admin.ModelAdmin):
    list_display = [
        'protocol', 'local_endpoint', 'remote_endpoint', 
        'state', 'process_name', 'timestamp'
    ]
    list_filter = ['protocol', 'state', 'timestamp']
    search_fields = ['local_address', 'remote_address', 'process_name']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    
    def local_endpoint(self, obj):
        return f"{obj.local_address}:{obj.local_port}"
    local_endpoint.short_description = "Local"
    
    def remote_endpoint(self, obj):
        if obj.remote_address and obj.remote_port:
            return f"{obj.remote_address}:{obj.remote_port}"
        return "N/A"
    remote_endpoint.short_description = "Remote"
    
    def get_queryset(self, request):
        # Limit to recent data to avoid performance issues
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        qs = super().get_queryset(request)
        cutoff = timezone.now() - timedelta(hours=1)
        return qs.filter(timestamp__gte=cutoff)


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'level_display', 'source', 'process', 
        'message_preview', 'hostname'
    ]
    list_filter = ['level', 'source', 'timestamp', 'facility']
    search_fields = ['message', 'process', 'hostname']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    
    def level_display(self, obj):
        colors = {
            'DEBUG': '#6c757d',
            'INFO': '#17a2b8',
            'WARNING': '#ffc107',
            'ERROR': '#dc3545',
            'CRITICAL': '#a71e2a'
        }
        color = colors.get(obj.level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.level
        )
    level_display.short_description = "Level"
    
    def message_preview(self, obj):
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
    message_preview.short_description = "Message"
    
    def get_queryset(self, request):
        # Limit to recent data to avoid performance issues
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        qs = super().get_queryset(request)
        cutoff = timezone.now() - timedelta(days=2)
        return qs.filter(timestamp__gte=cutoff)


@admin.register(MonitoringSettings)
class MonitoringSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'metric_retention_days', 'log_retention_days', 'collection_interval',
        'email_notifications_enabled', 'updated_at'
    ]
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Data Retention', {
            'fields': ('metric_retention_days', 'log_retention_days')
        }),
        ('Collection Settings', {
            'fields': (
                'collection_interval', 'temperature_monitoring_enabled',
                'network_monitoring_enabled', 'connection_monitoring_enabled',
                'log_aggregation_enabled'
            )
        }),
        ('Email Configuration', {
            'fields': (
                'email_notifications_enabled', 'smtp_host', 'smtp_port',
                'smtp_username', 'smtp_password', 'smtp_use_tls',
                'default_alert_email'
            )
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not MonitoringSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False


# Customize admin site
admin.site.site_header = "Router Manager - Monitoring Administration"
admin.site.site_title = "Router Manager Admin"
admin.site.index_title = "Monitoring System Administration"