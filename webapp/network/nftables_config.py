"""
NFTables configuration generator and applier
"""

import subprocess
import tempfile
import os
import logging
from django.conf import settings
from nftables_mgr.models import PortForward, NFTableRule

logger = logging.getLogger(__name__)

NFTABLES_CONFIG_PATH = "/etc/nftables/nftables.conf"
NFTABLES_BACKUP_PATH = "/etc/nftables/nftables.conf.backup"


class NFTablesConfigManager:
    """Manages nftables configuration generation and application"""

    def __init__(self):
        self.base_config = self._get_base_config()

    def _get_base_config(self):
        """Get the base nftables configuration"""
        return """#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority filter; policy accept;
        
        # Allow loopback
        iif lo accept
        
        # Allow established and related connections
        ct state established,related accept
        
        # Allow SSH
        tcp dport 22 accept
        
        # Allow HTTP/HTTPS
        tcp dport { 80, 443 } accept
        
        # Allow router-manager web interface
        tcp dport 8000 accept
        
        # Dynamic firewall rules will be inserted here
        # FIREWALL_RULES_PLACEHOLDER
        
        # Default drop for other traffic
        # drop
    }
    
    chain forward {
        type filter hook forward priority filter; policy accept;
        
        # Allow established and related connections
        ct state established,related accept
        
        # Dynamic port forwarding rules will be inserted here
        # FORWARD_RULES_PLACEHOLDER
    }
    
    chain output {
        type filter hook output priority filter; policy accept;
    }
}

table inet nat {
    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;
        
        # Dynamic DNAT rules for port forwarding will be inserted here
        # DNAT_RULES_PLACEHOLDER
    }
    
    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        
        # Masquerade for internal networks
        oifname "eth0" masquerade
    }
}
"""

    def generate_config(self):
        """Generate complete nftables configuration from database models"""
        config = self.base_config
        
        # Generate port forwarding rules
        port_forward_rules = self._generate_port_forward_rules()
        dnat_rules = self._generate_dnat_rules()
        firewall_rules = self._generate_firewall_rules()
        
        # Replace placeholders
        config = config.replace("        # FORWARD_RULES_PLACEHOLDER", port_forward_rules)
        config = config.replace("        # DNAT_RULES_PLACEHOLDER", dnat_rules)
        config = config.replace("        # FIREWALL_RULES_PLACEHOLDER", firewall_rules)
        
        return config

    def _generate_port_forward_rules(self):
        """Generate forward chain rules for port forwarding"""
        rules = []
        
        for pf in PortForward.objects.filter(enabled=True):
            rule = f"        # Port forward {pf.external_port} -> {pf.internal_ip}:{pf.internal_port}"
            rules.append(rule)
            
            if pf.protocol.lower() == 'both':
                protocols = ['tcp', 'udp']
            else:
                protocols = [pf.protocol.lower()]
            
            for proto in protocols:
                forward_rule = f"        ip daddr {pf.internal_ip} {proto} dport {pf.internal_port} accept"
                rules.append(forward_rule)
        
        return '\n'.join(rules) if rules else "        # No port forwarding rules"

    def _generate_dnat_rules(self):
        """Generate DNAT rules for port forwarding"""
        rules = []
        
        for pf in PortForward.objects.filter(enabled=True):
            rule = f"        # DNAT for port {pf.external_port} -> {pf.internal_ip}:{pf.internal_port}"
            rules.append(rule)
            
            if pf.protocol.lower() == 'both':
                protocols = ['tcp', 'udp']
            else:
                protocols = [pf.protocol.lower()]
            
            for proto in protocols:
                dnat_rule = f"        {proto} dport {pf.external_port} dnat to {pf.internal_ip}:{pf.internal_port}"
                rules.append(dnat_rule)
        
        return '\n'.join(rules) if rules else "        # No DNAT rules"

    def _generate_firewall_rules(self):
        """Generate firewall rules from NFTableRule models"""
        rules = []
        
        for rule in NFTableRule.objects.filter(enabled=True):
            comment = f"        # {rule.name}"
            rules.append(comment)
            
            # Generate nftables rule from NFTableRule model fields
            nft_rule = self._build_nftables_rule_from_model(rule)
            rules.append(f"        {nft_rule}")
        
        return '\n'.join(rules) if rules else "        # No custom firewall rules"

    def _build_nftables_rule_from_model(self, rule):
        """Build nftables rule from NFTableRule model fields"""
        rule_parts = []
        
        # Source IP
        if rule.source_ip:
            rule_parts.append(f"ip saddr {rule.source_ip}")
        
        # Destination IP  
        if rule.destination_ip:
            rule_parts.append(f"ip daddr {rule.destination_ip}")
        
        # Protocol and ports
        if rule.protocol and rule.protocol != 'all':
            if rule.protocol in ['tcp', 'udp']:
                # Start with protocol
                protocol_rule = rule.protocol
                
                # Add ports if specified
                port_parts = []
                if rule.source_port:
                    port_parts.append(f"sport {rule.source_port}")
                if rule.destination_port:
                    port_parts.append(f"dport {rule.destination_port}")
                
                if port_parts:
                    protocol_rule += ' ' + ' '.join(port_parts)
                
                rule_parts.append(protocol_rule)
            else:
                # For non-TCP/UDP protocols (like icmp)
                rule_parts.append(rule.protocol)
        else:
            # If no protocol specified but ports are, assume TCP
            if rule.source_port or rule.destination_port:
                port_parts = ['tcp']
                if rule.source_port:
                    port_parts.append(f"sport {rule.source_port}")
                if rule.destination_port:
                    port_parts.append(f"dport {rule.destination_port}")
                rule_parts.append(' '.join(port_parts))
        
        # Action
        rule_parts.append(rule.action)
        
        return ' '.join(rule_parts)

    def _format_nftable_rule(self, rule_text):
        """Format a raw nftables rule for insertion"""
        # Remove any leading/trailing whitespace and ensure proper formatting
        rule = rule_text.strip()
        
        # If the rule doesn't end with accept/drop/reject, assume it's accept
        if not any(rule.endswith(action) for action in ['accept', 'drop', 'reject', 'return']):
            rule += ' accept'
            
        return rule

    def backup_current_config(self):
        """Backup the current nftables configuration"""
        try:
            if os.path.exists(NFTABLES_CONFIG_PATH):
                subprocess.run([
                    'cp', NFTABLES_CONFIG_PATH, NFTABLES_BACKUP_PATH
                ], check=True)
                logger.info(f"Backed up nftables config to {NFTABLES_BACKUP_PATH}")
                return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to backup nftables config: {e}")
        return False

    def write_config(self, config_content):
        """Write configuration to nftables config file"""
        try:
            # Write to temporary file first
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.nft') as tmp_file:
                tmp_file.write(config_content)
                tmp_file_path = tmp_file.name

            # Test the configuration
            result = subprocess.run([
                'nft', '-c', '-f', tmp_file_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                os.unlink(tmp_file_path)
                logger.error(f"Invalid nftables configuration: {result.stderr}")
                return False, f"Configuration validation failed: {result.stderr}"

            # If validation passes, write to actual config file
            subprocess.run([
                'cp', tmp_file_path, NFTABLES_CONFIG_PATH
            ], check=True)
            
            # Clean up temp file
            os.unlink(tmp_file_path)
            
            logger.info(f"Successfully wrote nftables configuration to {NFTABLES_CONFIG_PATH}")
            return True, "Configuration written successfully"
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to write nftables config: {e}")
            return False, f"Failed to write configuration: {e}"
        except Exception as e:
            logger.error(f"Unexpected error writing config: {e}")
            return False, f"Unexpected error: {e}"

    def apply_config(self):
        """Apply the nftables configuration"""
        try:
            # First, let nftables read and apply the config file
            result = subprocess.run([
                'nft', '-f', NFTABLES_CONFIG_PATH
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to apply nftables config: {result.stderr}")
                return False, f"Failed to apply configuration: {result.stderr}"
            
            # Restart nftables service to ensure persistence
            result = subprocess.run([
                'systemctl', 'restart', 'nftables'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Failed to restart nftables service: {result.stderr}")
                # Don't fail here as the rules might still be applied
            
            logger.info("Successfully applied nftables configuration")
            return True, "Configuration applied successfully"
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply nftables config: {e}")
            return False, f"Failed to apply configuration: {e}"
        except Exception as e:
            logger.error(f"Unexpected error applying config: {e}")
            return False, f"Unexpected error: {e}"

    def rollback_config(self):
        """Rollback to the backup configuration"""
        try:
            if os.path.exists(NFTABLES_BACKUP_PATH):
                subprocess.run([
                    'cp', NFTABLES_BACKUP_PATH, NFTABLES_CONFIG_PATH
                ], check=True)
                
                # Apply the backup config
                subprocess.run([
                    'nft', '-f', NFTABLES_CONFIG_PATH
                ], check=True)
                
                logger.info("Successfully rolled back nftables configuration")
                return True, "Configuration rolled back successfully"
            else:
                logger.error("No backup configuration found")
                return False, "No backup configuration available"
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to rollback nftables config: {e}")
            return False, f"Rollback failed: {e}"

    def apply_network_changes(self):
        """Complete workflow to apply network configuration changes"""
        logger.info("Starting network configuration update")
        
        # Backup current config
        if not self.backup_current_config():
            return False, "Failed to backup current configuration"
        
        # Generate new configuration
        try:
            new_config = self.generate_config()
        except Exception as e:
            logger.error(f"Failed to generate configuration: {e}")
            return False, f"Configuration generation failed: {e}"
        
        # Write and validate configuration
        success, message = self.write_config(new_config)
        if not success:
            return False, message
        
        # Apply configuration
        success, message = self.apply_config()
        if not success:
            # Try to rollback on failure
            self.rollback_config()
            return False, message
        
        logger.info("Network configuration update completed successfully")
        return True, "Network configuration updated successfully"

    def get_current_config_summary(self):
        """Get a summary of current configuration from database"""
        summary = {
            'port_forwards': [],
            'firewall_rules': [],
        }
        
        # Port forwards
        for pf in PortForward.objects.all():
            summary['port_forwards'].append({
                'external_port': pf.external_port,
                'internal_ip': pf.internal_ip,
                'internal_port': pf.internal_port,
                'protocol': pf.protocol,
                'enabled': pf.enabled,
            })
        
        # Firewall rules
        for rule in NFTableRule.objects.all():
            summary['firewall_rules'].append({
                'name': rule.name,
                'protocol': rule.protocol,
                'source_ip': rule.source_ip,
                'source_port': rule.source_port,
                'destination_ip': rule.destination_ip,
                'destination_port': rule.destination_port,
                'action': rule.action,
                'enabled': rule.enabled,
            })
        
        return summary