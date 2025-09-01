from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class NginxProxyConfig(models.Model):
    """Model for storing nginx proxy configurations"""

    # Basic proxy configuration
    name = models.CharField(max_length=100, unique=True, help_text="Configuration name")
    description = models.TextField(
        blank=True, help_text="Description of this proxy configuration"
    )

    # Domain and SSL settings
    domain_name = models.CharField(
        max_length=255,
        help_text="Domain name for the proxy (e.g., example.com)",
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$",
                message="Enter a valid domain name",
            )
        ],
    )
    ssl_enabled = models.BooleanField(default=True, help_text="Enable SSL/HTTPS")
    auto_ssl = models.BooleanField(
        default=True,
        help_text="Automatically obtain SSL certificates via Let's Encrypt",
    )
    force_https = models.BooleanField(default=True, help_text="Redirect HTTP to HTTPS")

    # Upstream server settings
    upstream_host = models.CharField(
        max_length=255, default="127.0.0.1", help_text="Backend server host"
    )
    upstream_port = models.PositiveIntegerField(
        default=8000, help_text="Backend server port"
    )
    upstream_protocol = models.CharField(
        max_length=10,
        choices=[("http", "HTTP"), ("https", "HTTPS")],
        default="http",
        help_text="Backend server protocol",
    )

    # Proxy settings
    proxy_read_timeout = models.PositiveIntegerField(
        default=60, help_text="Proxy read timeout in seconds"
    )
    proxy_connect_timeout = models.PositiveIntegerField(
        default=60, help_text="Proxy connect timeout in seconds"
    )
    proxy_send_timeout = models.PositiveIntegerField(
        default=60, help_text="Proxy send timeout in seconds"
    )

    # Additional headers
    custom_headers = models.JSONField(
        default=dict, blank=True, help_text="Custom headers to add"
    )

    # Rate limiting
    rate_limit_enabled = models.BooleanField(
        default=False, help_text="Enable rate limiting"
    )
    rate_limit_rpm = models.PositiveIntegerField(
        default=100, help_text="Requests per minute limit"
    )

    # Access control
    access_log_enabled = models.BooleanField(
        default=True, help_text="Enable access logging"
    )
    error_log_enabled = models.BooleanField(
        default=True, help_text="Enable error logging"
    )

    # Configuration state
    is_active = models.BooleanField(
        default=False, help_text="Whether this configuration is active"
    )
    is_deployed = models.BooleanField(
        default=False, help_text="Whether this configuration is deployed"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deployed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Nginx Proxy Configuration"
        verbose_name_plural = "Nginx Proxy Configurations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.domain_name}"

    def get_upstream_url(self):
        """Get the full upstream URL"""
        return f"{self.upstream_protocol}://{self.upstream_host}:{self.upstream_port}"

    def mark_deployed(self):
        """Mark configuration as deployed"""
        self.is_deployed = True
        self.deployed_at = timezone.now()
        self.save()


class SSLCertificate(models.Model):
    """Model for tracking SSL certificates"""

    proxy_config = models.OneToOneField(
        NginxProxyConfig, on_delete=models.CASCADE, related_name="ssl_certificate"
    )

    # Certificate details
    certificate_path = models.CharField(
        max_length=500, help_text="Path to certificate file"
    )
    private_key_path = models.CharField(
        max_length=500, help_text="Path to private key file"
    )
    fullchain_path = models.CharField(
        max_length=500, help_text="Path to fullchain file"
    )

    # Certificate metadata
    issued_date = models.DateTimeField(help_text="When the certificate was issued")
    expiry_date = models.DateTimeField(help_text="When the certificate expires")
    issuer = models.CharField(
        max_length=255, default="Let's Encrypt", help_text="Certificate issuer"
    )

    # Status
    is_valid = models.BooleanField(
        default=True, help_text="Whether the certificate is valid"
    )
    auto_renewal = models.BooleanField(
        default=True, help_text="Auto-renew this certificate"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SSL Certificate"
        verbose_name_plural = "SSL Certificates"

    def __str__(self):
        return f"SSL for {self.proxy_config.domain_name}"

    def is_expiring_soon(self, days=30):
        """Check if certificate is expiring within specified days"""
        from datetime import timedelta

        return (self.expiry_date - timezone.now()) <= timedelta(days=days)


class NginxDeploymentLog(models.Model):
    """Model for tracking nginx deployment history"""

    proxy_config = models.ForeignKey(
        NginxProxyConfig, on_delete=models.CASCADE, related_name="deployment_logs"
    )

    # Deployment details
    action = models.CharField(
        max_length=20,
        choices=[
            ("deploy", "Deploy"),
            ("update", "Update"),
            ("remove", "Remove"),
            ("ssl_renew", "SSL Renewal"),
        ],
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("in_progress", "In Progress"),
        ],
        default="pending",
    )

    # Log details
    message = models.TextField(
        blank=True, help_text="Deployment message or error details"
    )
    config_snapshot = models.JSONField(
        help_text="Configuration snapshot at deployment time"
    )

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Nginx Deployment Log"
        verbose_name_plural = "Nginx Deployment Logs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.action} - {self.proxy_config.name} ({self.status})"

    def mark_completed(self, status, message=""):
        """Mark deployment as completed"""
        self.status = status
        self.message = message
        self.completed_at = timezone.now()
        self.save()
