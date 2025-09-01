"""
Monitoring utilities for system metrics collection
"""

import os
import json
import psutil
import subprocess
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import (
    MetricData, ServiceStatus, NetworkInterface, 
    ConnectionMonitor, SystemLog, Alert, AlertInstance
)
import logging

logger = logging.getLogger(__name__)


class SystemMonitor:
    """System monitoring and data collection"""

    def __init__(self):
        self.interfaces = []
        self.services_to_monitor = [
            'router-manager', 'nginx', 'postgresql', 'redis-server',
            'strongswan', 'nftables', 'ssh', 'systemd-networkd'
        ]

    def collect_all_metrics(self):
        """Collect all system metrics"""
        try:
            self.collect_cpu_metrics()
            self.collect_memory_metrics()
            self.collect_disk_metrics()
            self.collect_disk_io_metrics()
            self.collect_network_metrics()
            self.collect_load_metrics()
            self.collect_process_metrics()
            self.collect_connection_metrics()
            self.collect_temperature_metrics()
            self.update_service_status()
            self.check_alerts()
            logger.info("Metrics collection completed successfully")
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")

    def collect_cpu_metrics(self):
        """Collect CPU usage metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            MetricData.objects.create(
                metric_type='cpu',
                value=cpu_percent,
                unit='%',
                source='system'
            )

            # Per-CPU metrics
            per_cpu = psutil.cpu_percent(percpu=True, interval=0.1)
            for i, cpu_usage in enumerate(per_cpu):
                MetricData.objects.create(
                    metric_type='cpu',
                    value=cpu_usage,
                    unit='%',
                    source=f'cpu{i}'
                )
        except Exception as e:
            logger.error(f"Error collecting CPU metrics: {e}")

    def collect_memory_metrics(self):
        """Collect memory usage metrics"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            MetricData.objects.create(
                metric_type='memory',
                value=memory.percent,
                unit='%',
                source='system',
                metadata={
                    'total_mb': memory.total / (1024**2),
                    'available_mb': memory.available / (1024**2),
                    'used_mb': memory.used / (1024**2)
                }
            )

            MetricData.objects.create(
                metric_type='swap_usage',
                value=swap.percent,
                unit='%',
                source='system',
                metadata={
                    'total_mb': swap.total / (1024**2),
                    'used_mb': swap.used / (1024**2),
                    'free_mb': swap.free / (1024**2)
                }
            )
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")

    def collect_disk_metrics(self):
        """Collect disk usage metrics"""
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    MetricData.objects.create(
                        metric_type='disk',
                        value=(usage.used / usage.total) * 100,
                        unit='%',
                        source=partition.device,
                        metadata={
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total_gb': usage.total / (1024**3),
                            'used_gb': usage.used / (1024**3),
                            'free_gb': usage.free / (1024**3)
                        }
                    )
                except (PermissionError, OSError):
                    continue
        except Exception as e:
            logger.error(f"Error collecting disk metrics: {e}")

    def collect_disk_io_metrics(self):
        """Collect disk I/O metrics"""
        try:
            disk_io = psutil.disk_io_counters(perdisk=True)
            for device, io_stats in disk_io.items():
                MetricData.objects.create(
                    metric_type='disk_io_read',
                    value=io_stats.read_bytes,
                    unit='bytes',
                    source=device,
                    metadata={
                        'read_count': io_stats.read_count,
                        'read_time': io_stats.read_time
                    }
                )

                MetricData.objects.create(
                    metric_type='disk_io_write',
                    value=io_stats.write_bytes,
                    unit='bytes',
                    source=device,
                    metadata={
                        'write_count': io_stats.write_count,
                        'write_time': io_stats.write_time
                    }
                )
        except Exception as e:
            logger.error(f"Error collecting disk I/O metrics: {e}")

    def collect_network_metrics(self):
        """Collect network interface metrics"""
        try:
            net_io = psutil.net_io_counters(pernic=True)
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()

            for interface, io_stats in net_io.items():
                if interface == 'lo':  # Skip loopback
                    continue

                # Update interface info
                self.update_network_interface_info(interface, net_if_addrs, net_if_stats)

                # Collect metrics
                MetricData.objects.create(
                    metric_type='network_rx_bytes',
                    value=io_stats.bytes_recv,
                    unit='bytes',
                    source=interface,
                    metadata={
                        'packets_recv': io_stats.packets_recv,
                        'errin': io_stats.errin,
                        'dropin': io_stats.dropin
                    }
                )

                MetricData.objects.create(
                    metric_type='network_tx_bytes',
                    value=io_stats.bytes_sent,
                    unit='bytes',
                    source=interface,
                    metadata={
                        'packets_sent': io_stats.packets_sent,
                        'errout': io_stats.errout,
                        'dropout': io_stats.dropout
                    }
                )

                # Calculate bandwidth utilization if link speed is available
                interface_obj = NetworkInterface.objects.filter(interface_name=interface).first()
                if interface_obj and interface_obj.speed_mbps > 0:
                    # Calculate utilization based on recent data
                    recent_metrics = MetricData.objects.filter(
                        metric_type='network_tx_bytes',
                        source=interface,
                        timestamp__gte=timezone.now() - timedelta(minutes=1)
                    ).order_by('-timestamp')[:2]

                    if len(recent_metrics) == 2:
                        bytes_diff = recent_metrics[0].value - recent_metrics[1].value
                        time_diff = (recent_metrics[0].timestamp - recent_metrics[1].timestamp).total_seconds()
                        
                        if time_diff > 0:
                            mbps = (bytes_diff * 8) / (time_diff * 1024 * 1024)
                            utilization = (mbps / interface_obj.speed_mbps) * 100
                            
                            MetricData.objects.create(
                                metric_type='bandwidth_utilization',
                                value=utilization,
                                unit='%',
                                source=interface
                            )
        except Exception as e:
            logger.error(f"Error collecting network metrics: {e}")

    def update_network_interface_info(self, interface, net_if_addrs, net_if_stats):
        """Update network interface information"""
        try:
            interface_obj, created = NetworkInterface.objects.get_or_create(
                interface_name=interface,
                defaults={'display_name': interface}
            )

            # Update interface stats
            if interface in net_if_stats:
                stats = net_if_stats[interface]
                interface_obj.is_active = stats.isup
                interface_obj.speed_mbps = stats.speed if stats.speed != -1 else 0
                interface_obj.duplex = str(stats.duplex) if stats.duplex else ''
                interface_obj.mtu = stats.mtu

            # Update IP address
            if interface in net_if_addrs:
                for addr in net_if_addrs[interface]:
                    if addr.family == 2:  # IPv4
                        interface_obj.ip_address = addr.address
                        break

            interface_obj.save()
        except Exception as e:
            logger.error(f"Error updating interface {interface}: {e}")

    def collect_load_metrics(self):
        """Collect system load metrics"""
        try:
            load_avg = os.getloadavg()
            
            MetricData.objects.create(
                metric_type='load_1min',
                value=load_avg[0],
                unit='',
                source='system'
            )

            MetricData.objects.create(
                metric_type='load_5min',
                value=load_avg[1],
                unit='',
                source='system'
            )

            MetricData.objects.create(
                metric_type='load_15min',
                value=load_avg[2],
                unit='',
                source='system'
            )
        except Exception as e:
            logger.error(f"Error collecting load metrics: {e}")

    def collect_process_metrics(self):
        """Collect process metrics"""
        try:
            processes = psutil.pids()
            running_processes = 0
            
            for pid in processes:
                try:
                    p = psutil.Process(pid)
                    if p.status() == psutil.STATUS_RUNNING:
                        running_processes += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            MetricData.objects.create(
                metric_type='processes_total',
                value=len(processes),
                unit='',
                source='system'
            )

            MetricData.objects.create(
                metric_type='processes_running',
                value=running_processes,
                unit='',
                source='system'
            )
        except Exception as e:
            logger.error(f"Error collecting process metrics: {e}")

    def collect_connection_metrics(self):
        """Collect active connection metrics"""
        try:
            connections = psutil.net_connections()
            active_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
            
            MetricData.objects.create(
                metric_type='connections_active',
                value=len(connections),
                unit='',
                source='system'
            )

            MetricData.objects.create(
                metric_type='connections_established',
                value=active_connections,
                unit='',
                source='system'
            )

            # Store detailed connection info (limited to prevent DB bloat)
            ConnectionMonitor.objects.all().delete()  # Clear old data
            
            for conn in connections[:100]:  # Limit to 100 most recent
                try:
                    process_name = ""
                    process_id = conn.pid
                    
                    if conn.pid:
                        try:
                            process = psutil.Process(conn.pid)
                            process_name = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    ConnectionMonitor.objects.create(
                        protocol=conn.type.name.lower(),
                        local_address=conn.laddr.ip if conn.laddr else '',
                        local_port=conn.laddr.port if conn.laddr else 0,
                        remote_address=conn.raddr.ip if conn.raddr else '',
                        remote_port=conn.raddr.port if conn.raddr else None,
                        state=conn.status,
                        process_name=process_name,
                        process_id=process_id
                    )
                except Exception as e:
                    continue
        except Exception as e:
            logger.error(f"Error collecting connection metrics: {e}")

    def collect_temperature_metrics(self):
        """Collect temperature metrics"""
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            if entry.current:
                                MetricData.objects.create(
                                    metric_type='temperature',
                                    value=entry.current,
                                    unit='°C',
                                    source=f"{name}_{entry.label or 'sensor'}",
                                    metadata={
                                        'high': entry.high,
                                        'critical': entry.critical
                                    }
                                )
        except Exception as e:
            logger.error(f"Error collecting temperature metrics: {e}")

    def update_service_status(self):
        """Update service status information"""
        try:
            for service_name in self.services_to_monitor:
                try:
                    result = subprocess.run(
                        ['systemctl', 'is-active', service_name],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    status = 'running' if result.stdout.strip() == 'active' else 'stopped'
                    
                    # Get service uptime
                    uptime_seconds = 0
                    try:
                        uptime_result = subprocess.run(
                            ['systemctl', 'show', service_name, '--property=ActiveEnterTimestamp'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        if uptime_result.returncode == 0:
                            timestamp_line = uptime_result.stdout.strip()
                            if '=' in timestamp_line:
                                timestamp_str = timestamp_line.split('=', 1)[1]
                                if timestamp_str and timestamp_str != '':
                                    # Parse systemd timestamp and calculate uptime
                                    start_time = datetime.strptime(
                                        timestamp_str.split()[1] + ' ' + timestamp_str.split()[2],
                                        '%Y-%m-%d %H:%M:%S'
                                    )
                                    uptime_seconds = int((datetime.now() - start_time).total_seconds())
                    except:
                        pass

                    # Get process info if service is running
                    cpu_percent = 0
                    memory_percent = 0
                    memory_mb = 0
                    
                    if status == 'running':
                        try:
                            # Find process by service name
                            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                                try:
                                    if service_name in proc.info['name'] or \
                                       any(service_name in cmd for cmd in (proc.info['cmdline'] or [])):
                                        cpu_percent = proc.cpu_percent()
                                        memory_info = proc.memory_info()
                                        memory_mb = memory_info.rss / (1024**2)
                                        memory_percent = proc.memory_percent()
                                        break
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                        except:
                            pass

                    service_obj, created = ServiceStatus.objects.get_or_create(
                        service_name=service_name,
                        defaults={'display_name': service_name.replace('-', ' ').title()}
                    )
                    
                    service_obj.status = status
                    service_obj.last_checked = timezone.now()
                    service_obj.uptime_seconds = uptime_seconds
                    service_obj.cpu_percent = cpu_percent
                    service_obj.memory_percent = memory_percent
                    service_obj.memory_mb = memory_mb
                    service_obj.save()

                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout checking service {service_name}")
                except Exception as e:
                    logger.error(f"Error checking service {service_name}: {e}")
        except Exception as e:
            logger.error(f"Error updating service status: {e}")

    def check_alerts(self):
        """Check all active alerts against current metrics"""
        try:
            alerts = Alert.objects.filter(enabled=True)
            
            for alert in alerts:
                try:
                    # Get latest metric value
                    latest_metric = MetricData.objects.filter(
                        metric_type=alert.metric_type,
                        source=alert.source if alert.source else ''
                    ).first()

                    if not latest_metric:
                        continue

                    # Check if alert condition is met
                    should_trigger = self.evaluate_alert_condition(
                        latest_metric.value,
                        alert.comparison_operator,
                        alert.threshold_value
                    )

                    alert.last_checked = timezone.now()

                    if should_trigger:
                        # Check if alert was recently triggered to avoid spam
                        recent_trigger = AlertInstance.objects.filter(
                            alert=alert,
                            triggered_at__gte=timezone.now() - timedelta(minutes=alert.check_interval // 60)
                        ).exists()

                        if not recent_trigger:
                            # Create alert instance
                            alert_instance = AlertInstance.objects.create(
                                alert=alert,
                                value_at_trigger=latest_metric.value,
                                source=latest_metric.source,
                                message=f"Alert triggered: {alert.metric_type} {alert.comparison_operator} {alert.threshold_value}"
                            )

                            # Send notification
                            alert_instance.send_notification()
                            alert.last_triggered = timezone.now()

                    alert.save()

                except Exception as e:
                    logger.error(f"Error checking alert {alert.name}: {e}")

        except Exception as e:
            logger.error(f"Error in alert checking: {e}")

    def evaluate_alert_condition(self, current_value, operator, threshold):
        """Evaluate if alert condition is met"""
        if operator == '>':
            return current_value > threshold
        elif operator == '<':
            return current_value < threshold
        elif operator == '>=':
            return current_value >= threshold
        elif operator == '<=':
            return current_value <= threshold
        elif operator == '==':
            return current_value == threshold
        elif operator == '!=':
            return current_value != threshold
        return False

    def cleanup_old_data(self):
        """Clean up old monitoring data"""
        try:
            from .models import MonitoringSettings
            settings = MonitoringSettings.get_settings()
            
            # Clean up old metrics
            cutoff_date = timezone.now() - timedelta(days=settings.metric_retention_days)
            MetricData.objects.filter(timestamp__lt=cutoff_date).delete()
            
            # Clean up old logs
            log_cutoff_date = timezone.now() - timedelta(days=settings.log_retention_days)
            SystemLog.objects.filter(timestamp__lt=log_cutoff_date).delete()
            
            # Clean up old connections (keep only recent ones)
            ConnectionMonitor.objects.filter(
                timestamp__lt=timezone.now() - timedelta(hours=1)
            ).delete()
            
            logger.info("Data cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")


def collect_system_logs():
    """Collect and parse system logs"""
    try:
        # Parse recent syslog entries
        log_files = [
            '/var/log/syslog',
            '/var/log/messages',
            '/var/log/auth.log',
            '/var/log/daemon.log'
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    # Read last 100 lines
                    result = subprocess.run(
                        ['tail', '-n', '100', log_file],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        parse_syslog_entries(result.stdout, os.path.basename(log_file))
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout reading log file {log_file}")
                except Exception as e:
                    logger.error(f"Error reading log file {log_file}: {e}")
                    
    except Exception as e:
        logger.error(f"Error collecting system logs: {e}")


def parse_syslog_entries(log_content, source):
    """Parse syslog entries and store them"""
    try:
        lines = log_content.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                # Basic syslog parsing
                # Format: timestamp hostname process[pid]: message
                parts = line.split(' ', 5)
                if len(parts) < 6:
                    continue
                    
                # Extract timestamp (assuming current year)
                timestamp_str = f"{datetime.now().year} {parts[0]} {parts[1]} {parts[2]}"
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
                    timestamp = timezone.make_aware(timestamp)
                except:
                    timestamp = timezone.now()
                
                hostname = parts[3]
                process_info = parts[4] if len(parts) > 4 else ""
                message = parts[5] if len(parts) > 5 else line
                
                # Extract process name and determine log level
                process_name = process_info.split('[')[0] if '[' in process_info else process_info
                
                # Determine log level from message content
                message_lower = message.lower()
                if any(word in message_lower for word in ['error', 'failed', 'fail']):
                    level = 'ERROR'
                elif any(word in message_lower for word in ['warn', 'warning']):
                    level = 'WARNING'
                elif any(word in message_lower for word in ['info', 'start', 'stop']):
                    level = 'INFO'
                else:
                    level = 'INFO'
                
                # Determine source category
                if 'kernel' in process_name:
                    log_source = 'kernel'
                elif any(auth in process_name for auth in ['auth', 'ssh', 'sudo']):
                    log_source = 'auth'
                elif 'nginx' in process_name:
                    log_source = 'nginx'
                elif 'router-manager' in process_name:
                    log_source = 'router-manager'
                elif any(vpn in process_name for vpn in ['strongswan', 'charon']):
                    log_source = 'vpn'
                else:
                    log_source = 'system'
                
                # Store log entry (avoid duplicates)
                SystemLog.objects.get_or_create(
                    source=log_source,
                    level=level,
                    message=message,
                    timestamp=timestamp,
                    defaults={
                        'hostname': hostname,
                        'process': process_name,
                        'facility': source
                    }
                )
                
            except Exception as e:
                continue  # Skip malformed entries
                
    except Exception as e:
        logger.error(f"Error parsing syslog entries: {e}")