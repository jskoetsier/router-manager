"""
Monitoring models
"""

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.conf import settings
import json


class MetricData(models.Model):
    """Historical metric data for monitoring"""

    METRIC_TYPES = [
        ("cpu", "CPU Usage"),
        ("memory", "Memory Usage"),
        ("disk", "Disk Usage"),
        ("disk_io_read", "Disk I/O Read"),
        ("disk_io_write", "Disk I/O Write"),
        ("network_rx", "Network RX"),
        ("network_tx", "Network TX"),
        ("network_rx_bytes", "Network RX Bytes"),
        ("network_tx_bytes", "Network TX Bytes"),
        ("network_packets_rx", "Network Packets RX"),
        ("network_packets_tx", "Network Packets TX"),
        ("network_errors", "Network Errors"),
        ("load", "System Load"),
        ("load_1min", "Load 1min"),
        ("load_5min", "Load 5min"),
        ("load_15min", "Load 15min"),
        ("temperature", "Temperature"),
        ("bandwidth_utilization", "Bandwidth Utilization"),
        ("connections_active", "Active Connections"),
        ("connections_established", "Established Connections"),
        ("processes_running", "Running Processes"),
        ("processes_total", "Total Processes"),
        ("swap_usage", "Swap Usage"),
        ("uptime", "System Uptime"),
        ("interrupts", "Interrupts"),
        ("context_switches", "Context Switches"),
    ]

    metric_type = models.CharField(max_length=30, choices=METRIC_TYPES)
    value = models.FloatField()
    unit = models.CharField(max_length=20, blank=True)
    source = models.CharField(max_length=100, blank=True)  # Interface name, disk, etc.
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)  # Additional metric details

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["metric_type", "timestamp"]),
            models.Index(fields=["source", "metric_type", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.metric_type} ({self.source}): {self.value}"


class Alert(models.Model):
    """Monitoring alerts"""

    ALERT_TYPES = [
        ("threshold", "Threshold Alert"),
        ("anomaly", "Anomaly Detection"),
        ("service", "Service Alert"),
        ("network", "Network Alert"),
        ("custom", "Custom Alert"),
    ]

    SEVERITY_LEVELS = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("critical", "Critical"),
    ]

    name = models.CharField(max_length=100)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    metric_type = models.CharField(max_length=30, choices=MetricData.METRIC_TYPES)
    threshold_value = models.FloatField()
    comparison_operator = models.CharField(
        max_length=5,
        choices=[
            (">", "Greater than"),
            ("<", "Less than"),
            (">=", "Greater or equal"),
            ("<=", "Less or equal"),
            ("==", "Equal"),
            ("!=", "Not equal"),
        ],
    )
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    enabled = models.BooleanField(default=True)
    notification_enabled = models.BooleanField(default=True)
    email_recipients = models.JSONField(default=list, blank=True)
    check_interval = models.IntegerField(default=60, help_text="Check interval in seconds")
    source = models.CharField(max_length=100, blank=True, help_text="Specific source to monitor")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monitoring_alerts_created')
    created_at = models.DateTimeField(default=timezone.now)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_triggered = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.metric_type} {self.comparison_operator} {self.threshold_value})"


class AlertInstance(models.Model):
    """Individual alert instances/triggers"""

    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='instances')
    triggered_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    value_at_trigger = models.FloatField()
    source = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-triggered_at"]

    @property
    def is_resolved(self):
        return self.resolved_at is not None

    def send_notification(self):
        """Send email notification for this alert instance"""
        if not self.alert.notification_enabled or self.notification_sent:
            return

        recipients = self.alert.email_recipients
        if not recipients:
            return

        subject = f"Alert: {self.alert.name} - {self.alert.severity.upper()}"

        message = f"""
Alert Triggered: {self.alert.name}
Severity: {self.alert.severity.upper()}
Metric: {self.alert.metric_type}
Current Value: {self.value_at_trigger} {self.alert.threshold_value}
Threshold: {self.alert.comparison_operator} {self.alert.threshold_value}
Source: {self.source or 'System'}
Time: {self.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Additional Details:
{self.message}
"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
            self.notification_sent = True
            self.save(update_fields=['notification_sent'])
        except Exception as e:
            # Log the error but don't raise it
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send alert notification: {e}")


class ServiceStatus(models.Model):
    """Service monitoring status"""

    service_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "Running"),
            ("stopped", "Stopped"),
            ("failed", "Failed"),
            ("unknown", "Unknown"),
        ],
    )
    last_checked = models.DateTimeField(default=timezone.now)
    uptime_seconds = models.BigIntegerField(default=0)
    cpu_percent = models.FloatField(default=0)
    memory_percent = models.FloatField(default=0)
    memory_mb = models.FloatField(default=0)

    class Meta:
        ordering = ["service_name"]

    def __str__(self):
        return f"{self.display_name or self.service_name} ({self.status})"


class NetworkInterface(models.Model):
    """Network interface monitoring"""

    interface_name = models.CharField(max_length=50)
    display_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    mac_address = models.CharField(max_length=17, blank=True)
    mtu = models.IntegerField(default=1500)
    speed_mbps = models.FloatField(default=0)  # Link speed in Mbps
    duplex = models.CharField(max_length=20, blank=True)
    monitor_enabled = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["interface_name"]
        unique_together = ["interface_name"]

    def __str__(self):
        return f"{self.display_name or self.interface_name} ({self.ip_address})"


class ConnectionMonitor(models.Model):
    """Active network connections monitoring"""

    protocol = models.CharField(max_length=10)
    local_address = models.CharField(max_length=100)
    local_port = models.IntegerField()
    remote_address = models.CharField(max_length=100, blank=True)
    remote_port = models.IntegerField(null=True, blank=True)
    state = models.CharField(max_length=20)
    process_name = models.CharField(max_length=100, blank=True)
    process_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["protocol", "timestamp"]),
            models.Index(fields=["state", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.protocol} {self.local_address}:{self.local_port} -> {self.remote_address}:{self.remote_port} ({self.state})"


class SystemLog(models.Model):
    """System log aggregation"""

    LOG_LEVELS = [
        ("DEBUG", "Debug"),
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("CRITICAL", "Critical"),
    ]

    LOG_SOURCES = [
        ("system", "System"),
        ("kernel", "Kernel"),
        ("auth", "Authentication"),
        ("daemon", "Daemon"),
        ("mail", "Mail"),
        ("user", "User"),
        ("local", "Local"),
        ("router-manager", "Router Manager"),
        ("nginx", "Nginx"),
        ("vpn", "VPN"),
        ("firewall", "Firewall"),
    ]

    source = models.CharField(max_length=20, choices=LOG_SOURCES)
    level = models.CharField(max_length=10, choices=LOG_LEVELS)
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    facility = models.CharField(max_length=50, blank=True)
    hostname = models.CharField(max_length=100, blank=True)
    process = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["source", "timestamp"]),
            models.Index(fields=["level", "timestamp"]),
        ]

    def __str__(self):
        return f"[{self.level}] {self.source}: {self.message[:100]}..."


class MonitoringSettings(models.Model):
    """Global monitoring configuration"""

    metric_retention_days = models.IntegerField(default=30)
    log_retention_days = models.IntegerField(default=7)
    collection_interval = models.IntegerField(default=30, help_text="Seconds between metric collections")
    email_notifications_enabled = models.BooleanField(default=True)
    smtp_host = models.CharField(max_length=100, blank=True)
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=100, blank=True)
    smtp_password = models.CharField(max_length=100, blank=True)
    smtp_use_tls = models.BooleanField(default=True)
    default_alert_email = models.EmailField(blank=True)
    temperature_monitoring_enabled = models.BooleanField(default=True)
    network_monitoring_enabled = models.BooleanField(default=True)
    connection_monitoring_enabled = models.BooleanField(default=True)
    log_aggregation_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Monitoring Settings"
        verbose_name_plural = "Monitoring Settings"

    def save(self, *args, **kwargs):
        # Ensure only one settings instance exists
        if not self.pk and MonitoringSettings.objects.exists():
            self.pk = MonitoringSettings.objects.first().pk
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        settings, created = cls.objects.get_or_create(defaults={})
        return settings
