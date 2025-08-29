from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import NginxProxyConfig, SSLCertificate, NginxDeploymentLog


@admin.register(NginxProxyConfig)
class NginxProxyConfigAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'domain_name', 'upstream_display', 'ssl_status', 
        'is_active', 'is_deployed', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_deployed', 'ssl_enabled', 'auto_ssl', 
        'upstream_protocol', 'created_at'
    ]
    search_fields = ['name', 'domain_name', 'upstream_host', 'description']
    readonly_fields = ['created_at', 'updated_at', 'deployed_at']
    
    fieldsets = (
        ('Basic Configuration', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Domain & SSL Settings', {
            'fields': ('domain_name', 'ssl_enabled', 'auto_ssl', 'force_https')
        }),
        ('Upstream Server', {
            'fields': ('upstream_host', 'upstream_port', 'upstream_protocol')
        }),
        ('Proxy Settings', {
            'fields': ('proxy_read_timeout', 'proxy_connect_timeout', 'proxy_send_timeout'),
            'classes': ('collapse',)
        }),
        ('Security & Rate Limiting', {
            'fields': ('rate_limit_enabled', 'rate_limit_rpm'),
            'classes': ('collapse',)
        }),
        ('Custom Headers', {
            'fields': ('custom_headers',),
            'classes': ('collapse',)
        }),
        ('Logging', {
            'fields': ('access_log_enabled', 'error_log_enabled'),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_deployed', 'created_at', 'updated_at', 'deployed_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['deploy_selected', 'undeploy_selected', 'activate_selected', 'deactivate_selected']
    
    def upstream_display(self, obj):
        """Display upstream server info"""
        return f"{obj.upstream_protocol}://{obj.upstream_host}:{obj.upstream_port}"
    upstream_display.short_description = "Upstream Server"
    
    def ssl_status(self, obj):
        """Display SSL status with visual indicators"""
        if not obj.ssl_enabled:
            return format_html('<span class="badge badge-secondary">SSL Disabled</span>')
        
        if obj.auto_ssl:
            if hasattr(obj, 'ssl_certificate'):
                cert = obj.ssl_certificate
                if cert.is_expiring_soon():
                    return format_html('<span class="badge badge-warning">SSL Expiring Soon</span>')
                else:
                    return format_html('<span class="badge badge-success">SSL Active</span>')
            else:
                return format_html('<span class="badge badge-info">SSL Pending</span>')
        else:
            return format_html('<span class="badge badge-primary">Manual SSL</span>')
    ssl_status.short_description = "SSL Status"
    
    def deploy_selected(self, request, queryset):
        """Deploy selected configurations"""
        # This would need to be implemented with proper deployment logic
        for config in queryset:
            if not config.is_deployed:
                # Here you would call the deployment logic
                pass
        self.message_user(request, f"Deployment initiated for {queryset.count()} configurations.")
    deploy_selected.short_description = "Deploy selected configurations"
    
    def undeploy_selected(self, request, queryset):
        """Remove selected configurations from deployment"""
        for config in queryset.filter(is_deployed=True):
            # Here you would call the undeployment logic
            pass
        self.message_user(request, f"Removal initiated for deployed configurations.")
    undeploy_selected.short_description = "Remove selected from deployment"
    
    def activate_selected(self, request, queryset):
        """Activate selected configurations"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} configurations activated.")
    activate_selected.short_description = "Activate selected configurations"
    
    def deactivate_selected(self, request, queryset):
        """Deactivate selected configurations"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} configurations deactivated.")
    deactivate_selected.short_description = "Deactivate selected configurations"


@admin.register(SSLCertificate)
class SSLCertificateAdmin(admin.ModelAdmin):
    list_display = [
        'proxy_config', 'issuer', 'issued_date', 'expiry_date', 
        'expiry_status', 'is_valid', 'auto_renewal'
    ]
    list_filter = ['issuer', 'is_valid', 'auto_renewal', 'issued_date', 'expiry_date']
    search_fields = ['proxy_config__name', 'proxy_config__domain_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Certificate Information', {
            'fields': ('proxy_config', 'issuer', 'issued_date', 'expiry_date')
        }),
        ('File Paths', {
            'fields': ('certificate_path', 'private_key_path', 'fullchain_path'),
            'classes': ('collapse',)
        }),
        ('Status & Settings', {
            'fields': ('is_valid', 'auto_renewal', 'created_at', 'updated_at')
        })
    )
    
    def expiry_status(self, obj):
        """Display certificate expiry status"""
        days_left = (obj.expiry_date - timezone.now()).days
        
        if days_left < 0:
            return format_html('<span class="badge badge-danger">Expired</span>')
        elif days_left < 7:
            return format_html('<span class="badge badge-danger">{} days left</span>', days_left)
        elif days_left < 30:
            return format_html('<span class="badge badge-warning">{} days left</span>', days_left)
        else:
            return format_html('<span class="badge badge-success">{} days left</span>', days_left)
    expiry_status.short_description = "Expiry Status"


@admin.register(NginxDeploymentLog)
class NginxDeploymentLogAdmin(admin.ModelAdmin):
    list_display = [
        'proxy_config', 'action', 'status', 'started_at', 
        'completed_at', 'duration', 'message_preview'
    ]
    list_filter = ['action', 'status', 'started_at']
    search_fields = ['proxy_config__name', 'message']
    readonly_fields = ['started_at', 'completed_at', 'duration']
    
    fieldsets = (
        ('Deployment Information', {
            'fields': ('proxy_config', 'action', 'status')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration')
        }),
        ('Details', {
            'fields': ('message', 'config_snapshot'),
            'classes': ('collapse',)
        })
    )
    
    def duration(self, obj):
        """Calculate and display deployment duration"""
        if obj.completed_at and obj.started_at:
            duration = obj.completed_at - obj.started_at
            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "-"
    duration.short_description = "Duration"
    
    def message_preview(self, obj):
        """Display a preview of the message"""
        if obj.message:
            return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
        return "-"
    message_preview.short_description = "Message"