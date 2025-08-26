"""
VPN management models
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class VPNTunnel(models.Model):
    """IPSec VPN tunnel configuration"""

    TUNNEL_TYPES = [
        ("site-to-site", "Site-to-Site"),
        ("roadwarrior", "Road Warrior"),
        ("client", "Client VPN"),
    ]

    STATUS_CHOICES = [
        ("up", "Connected"),
        ("down", "Disconnected"),
        ("connecting", "Connecting"),
        ("error", "Error"),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    tunnel_type = models.CharField(max_length=20, choices=TUNNEL_TYPES)
    local_ip = models.GenericIPAddressField()
    remote_ip = models.GenericIPAddressField()
    local_subnet = models.CharField(max_length=50)
    remote_subnet = models.CharField(max_length=50)
    pre_shared_key = models.CharField(max_length=255)
    encryption = models.CharField(max_length=50, default="aes256")
    authentication = models.CharField(max_length=50, default="sha256")
    dh_group = models.CharField(max_length=20, default="modp2048")
    enabled = models.BooleanField(default=True)
    auto_start = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="down")
    last_connected = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]


class Certificate(models.Model):
    """SSL/TLS Certificate for VPN"""

    CERT_TYPES = [
        ("ca", "Certificate Authority"),
        ("server", "Server Certificate"),
        ("client", "Client Certificate"),
    ]

    name = models.CharField(max_length=100)
    cert_type = models.CharField(max_length=10, choices=CERT_TYPES)
    certificate = models.TextField()
    private_key = models.TextField(blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    issuer = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["name"]


class VPNUser(models.Model):
    """VPN user for client connections"""

    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    enabled = models.BooleanField(default=True)
    certificate = models.ForeignKey(
        Certificate, on_delete=models.SET_NULL, null=True, blank=True
    )
    allowed_ips = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["username"]
