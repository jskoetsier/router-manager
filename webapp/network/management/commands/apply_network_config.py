"""
Management command to apply network configuration from database to nftables
"""

from django.core.management.base import BaseCommand
from network.nftables_config import NFTablesConfigManager
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Apply network configuration from database to nftables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually applying changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create backup before applying changes (default: True)',
            default=True
        )

    def handle(self, *args, **options):
        nft_manager = NFTablesConfigManager()
        
        if options['verbose']:
            self.stdout.write('Loading network configuration from database...')
        
        # Get current configuration summary
        config_summary = nft_manager.get_current_config_summary()
        
        self.stdout.write(self.style.SUCCESS('Current Database Configuration:'))
        self.stdout.write(f"Port Forwards: {len(config_summary['port_forwards'])}")
        for pf in config_summary['port_forwards']:
            status = "enabled" if pf['enabled'] else "disabled"
            self.stdout.write(f"  {pf['external_port']}/{pf['protocol']} -> {pf['internal_ip']}:{pf['internal_port']} ({status})")
        
        self.stdout.write(f"\nFirewall Rules: {len(config_summary['firewall_rules'])}")
        for rule in config_summary['firewall_rules']:
            status = "enabled" if rule['enabled'] else "disabled"
            self.stdout.write(f"  {rule['name']}: {rule['rule']} ({status})")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\nDry run - generating configuration without applying...'))
            try:
                config_content = nft_manager.generate_config()
                self.stdout.write('\nGenerated nftables configuration:')
                self.stdout.write('-' * 50)
                self.stdout.write(config_content)
                self.stdout.write('-' * 50)
                self.stdout.write(self.style.SUCCESS('Configuration generated successfully (not applied)'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error generating configuration: {e}'))
        else:
            self.stdout.write('\nApplying network configuration...')
            
            try:
                success, message = nft_manager.apply_network_changes()
                
                if success:
                    self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ {message}'))
                    return
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error applying configuration: {e}'))
                return
        
        self.stdout.write(self.style.SUCCESS('\nNetwork configuration process completed.'))