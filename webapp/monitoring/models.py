"""
Monitoring models
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class MetricData(models.Model):
    """Historical metric data for monitoring"""
    METRIC_TYPES = [
        ('cpu', 'CPU Usage'),
        ('memory', 'Memory Usage'),
        ('disk', 'Disk Usage'),
        ('network_rx', 'Network RX'),
        ('network_tx', 'Network TX'),
        ('load', 'System Load'),
        ('temperature', 'Temperature'),
        ('bandwidth', 'Bandwidth'),
    ]
    
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    value = models.FloatField()
    unit = models.CharField(max_length=20, blank=True)
    source = models.CharField(max_length=100, blank=True)  # Interface name, disk, etc.
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_type', 'timestamp']),
            models.Index(fields=['source', 'metric_type', 'timestamp']),
        ]


class Alert(models.Model):
    """Monitoring alerts"""
    ALERT_TYPES = [
        ('threshold', 'Threshold Alert'),
        ('anomaly', 'Anomaly Detection'),
        ('service', 'Service Alert'),
        ('custom', 'Custom Alert'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(max_length=100)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    metric_type = models.CharField(max_length=20, choices=MetricData.METRIC_TYPES)
    threshold_value = models.FloatField()
    comparison_operator = models.CharField(max_length=5, choices=[
        ('>', 'Greater than'),
        ('<', 'Less than'),
        ('>=', 'Greater or equal'),
        ('<=', 'Less or equal'),
        ('==', 'Equal'),
        ('!=', 'Not equal'),
    ])
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    enabled = models.BooleanField(default=True)
    notification_enabled = models.BooleanField(default=True)
    email_recipients = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['name']


class ServiceStatus(models.Model):
    """Service monitoring status"""
    service_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('failed', 'Failed'),
        ('unknown', 'Unknown'),
    ])
    last_checked = models.DateTimeField(default=timezone.now)
    uptime_seconds = models.BigIntegerField(default=0)
    
    class Meta:
        ordering = ['service_name']