"""
Celery tasks for monitoring
"""

from celery import shared_task
from django.conf import settings
import logging
from .utils import SystemMonitor, collect_system_logs

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def collect_system_metrics(self):
    """Periodic task to collect system metrics"""
    try:
        logger.info("Starting system metrics collection")
        monitor = SystemMonitor()
        monitor.collect_all_metrics()
        logger.info("System metrics collection completed")
        return "Metrics collection completed successfully"
    except Exception as e:
        logger.error(f"Error in metrics collection task: {e}")
        self.retry(countdown=60, max_retries=3)


@shared_task(bind=True)
def collect_logs_task(self):
    """Periodic task to collect and parse system logs"""
    try:
        logger.info("Starting system logs collection")
        collect_system_logs()
        logger.info("System logs collection completed")
        return "Logs collection completed successfully"
    except Exception as e:
        logger.error(f"Error in logs collection task: {e}")
        self.retry(countdown=60, max_retries=3)


@shared_task(bind=True)
def cleanup_old_data(self):
    """Periodic task to cleanup old monitoring data"""
    try:
        logger.info("Starting data cleanup")
        monitor = SystemMonitor()
        monitor.cleanup_old_data()
        logger.info("Data cleanup completed")
        return "Data cleanup completed successfully"
    except Exception as e:
        logger.error(f"Error in data cleanup task: {e}")
        self.retry(countdown=300, max_retries=2)


@shared_task(bind=True)
def check_system_health(self):
    """Check overall system health and generate summary"""
    try:
        logger.info("Performing system health check")

        from .models import MetricData, AlertInstance, ServiceStatus
        from django.utils import timezone
        from datetime import timedelta

        # Check for critical alerts in the last hour
        recent_alerts = AlertInstance.objects.filter(
            triggered_at__gte=timezone.now() - timedelta(hours=1),
            alert__severity='critical'
        ).count()

        # Check service status
        failed_services = ServiceStatus.objects.filter(status='failed').count()

        # Check recent metrics availability
        recent_metrics = MetricData.objects.filter(
            timestamp__gte=timezone.now() - timedelta(minutes=10)
        ).count()

        health_data = {
            'recent_critical_alerts': recent_alerts,
            'failed_services': failed_services,
            'recent_metrics_count': recent_metrics,
            'check_time': timezone.now().isoformat()
        }

        logger.info(f"System health check completed: {health_data}")
        return health_data

    except Exception as e:
        logger.error(f"Error in health check task: {e}")
        self.retry(countdown=300, max_retries=2)
