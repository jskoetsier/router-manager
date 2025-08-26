"""
Network management models
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class NetworkInterface(models.Model):
    """Network interface configuration"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    interface_type = models.CharField(max_length=20, default='ethernet')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    netmask = models.GenericIPAddressField(null=True, blank=True)
    gateway = models.GenericIPAddressField(null=True, blank=True)
    dns_servers = models.JSONField(default=list, blank=True)
    dhcp_enabled = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    mtu = models.PositiveIntegerField(default=1500)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['name']


class Route(models.Model):
    """Network routing table entry"""
    destination = models.CharField(max_length=50)  # Network/CIDR
    gateway = models.GenericIPAddressField()
    interface = models.ForeignKey(NetworkInterface, on_delete=models.CASCADE)
    metric = models.PositiveIntegerField(default=100)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['metric', 'destination']


class SystemSetting(models.Model):
    """System network settings"""
    ip_forwarding = models.BooleanField(default=False)
    ipv6_forwarding = models.BooleanField(default=False)
    nat_enabled = models.BooleanField(default=False)
    nat_interface = models.CharField(max_length=50, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)