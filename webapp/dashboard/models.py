"""
Dashboard models for Router Manager
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SystemStatus(models.Model):
    """System status tracking"""
    timestamp = models.DateTimeField(default=timezone.now)
    cpu_usage = models.FloatField()
    memory_usage = models.FloatField()
    disk_usage = models.FloatField()
    network_rx = models.BigIntegerField(default=0)
    network_tx = models.BigIntegerField(default=0)
    
    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'


class UserActivity(models.Model):
    """User activity logging"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-timestamp']


class Alert(models.Model):
    """System alerts"""
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']


class Configuration(models.Model):
    """System configuration settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['key']