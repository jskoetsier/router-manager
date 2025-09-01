"""
nftables management models
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class NFTableRule(models.Model):
    """nftables firewall rule"""

    PROTOCOL_CHOICES = [
        ("tcp", "TCP"),
        ("udp", "UDP"),
        ("icmp", "ICMP"),
        ("all", "All"),
    ]

    ACTION_CHOICES = [
        ("accept", "Accept"),
        ("drop", "Drop"),
        ("reject", "Reject"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    protocol = models.CharField(max_length=10, choices=PROTOCOL_CHOICES)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    source_port = models.PositiveIntegerField(null=True, blank=True)
    destination_ip = models.GenericIPAddressField(null=True, blank=True)
    destination_port = models.PositiveIntegerField(null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    enabled = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["priority", "name"]


class PortForward(models.Model):
    """Port forwarding rule"""

    name = models.CharField(max_length=100)
    external_port = models.PositiveIntegerField()
    internal_ip = models.GenericIPAddressField()
    internal_port = models.PositiveIntegerField()
    protocol = models.CharField(max_length=10, choices=NFTableRule.PROTOCOL_CHOICES[:2])
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ["external_port", "protocol"]
        ordering = ["external_port"]


# Signal handlers to automatically apply network configuration changes
@receiver(post_save, sender=NFTableRule)
@receiver(post_save, sender=PortForward)
def apply_network_config_on_save(sender, instance, **kwargs):
    """Apply network configuration when NFTableRule or PortForward is saved"""
    try:
        from network.nftables_config import NFTablesConfigManager
        nft_manager = NFTablesConfigManager()
        success, message = nft_manager.apply_network_changes()
        if not success:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to apply network config after {sender.__name__} save: {message}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Exception applying network config after {sender.__name__} save: {e}")


@receiver(post_delete, sender=NFTableRule)
@receiver(post_delete, sender=PortForward)
def apply_network_config_on_delete(sender, instance, **kwargs):
    """Apply network configuration when NFTableRule or PortForward is deleted"""
    try:
        from network.nftables_config import NFTablesConfigManager
        nft_manager = NFTablesConfigManager()
        success, message = nft_manager.apply_network_changes()
        if not success:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to apply network config after {sender.__name__} delete: {message}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Exception applying network config after {sender.__name__} delete: {e}")
