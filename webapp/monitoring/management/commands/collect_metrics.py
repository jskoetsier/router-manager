"""
Management command to collect system metrics
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from monitoring.utils import SystemMonitor, collect_system_logs
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Collect system metrics and store in database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run collection once instead of continuous monitoring',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )

    def handle(self, *args, **options):
        if options['verbose']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Starting metric collection at {timezone.now()}'
                )
            )

        try:
            monitor = SystemMonitor()

            # Collect system metrics
            self.stdout.write('Collecting system metrics...')
            monitor.collect_all_metrics()

            # Collect system logs
            self.stdout.write('Collecting system logs...')
            collect_system_logs()

            # Clean up old data
            self.stdout.write('Cleaning up old data...')
            monitor.cleanup_old_data()

            if options['verbose']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Metric collection completed at {timezone.now()}'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during metric collection: {e}')
            )
            logger.error(f'Error during metric collection: {e}')
            raise
