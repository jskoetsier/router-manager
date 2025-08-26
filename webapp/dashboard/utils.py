"""
Utility functions for Router Manager dashboard
"""
import psutil
import subprocess
import platform
import socket
from datetime import datetime
from .models import UserActivity


def log_user_activity(user, action, ip_address, success=True, description=''):
    """Log user activity"""
    UserActivity.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=ip_address,
        success=success
    )


def get_system_info():
    """Get comprehensive system information"""
    try:
        # System information
        uname = platform.uname()
        
        # CPU information
        cpu_info = {
            'physical_cores': psutil.cpu_count(logical=False),
            'total_cores': psutil.cpu_count(logical=True),
            'max_frequency': f"{psutil.cpu_freq().max:.2f}Mhz" if psutil.cpu_freq() else 'N/A',
            'current_frequency': f"{psutil.cpu_freq().current:.2f}Mhz" if psutil.cpu_freq() else 'N/A',
            'usage': f"{psutil.cpu_percent(interval=1)}%"
        }
        
        # Memory information
        memory = psutil.virtual_memory()
        memory_info = {
            'total': format_bytes(memory.total),
            'available': format_bytes(memory.available),
            'used': format_bytes(memory.used),
            'percentage': f"{memory.percent}%"
        }
        
        # Disk information
        disk = psutil.disk_usage('/')
        disk_info = {
            'total': format_bytes(disk.total),
            'used': format_bytes(disk.used),
            'free': format_bytes(disk.free),
            'percentage': f"{(disk.used / disk.total) * 100:.1f}%"
        }
        
        # Network information
        hostname = socket.gethostname()
        
        # Boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        system_info = {
            'system': uname.system,
            'node_name': uname.node,
            'release': uname.release,
            'version': uname.version,
            'machine': uname.machine,
            'processor': uname.processor,
            'hostname': hostname,
            'boot_time': boot_time,
            'cpu': cpu_info,
            'memory': memory_info,
            'disk': disk_info,
        }
        
        return system_info
    
    except Exception as e:
        return {'error': str(e)}


def get_network_interfaces():
    """Get network interface information"""
    try:
        interfaces = {}
        
        # Get network interface statistics
        net_io = psutil.net_io_counters(pernic=True)
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        for interface_name in net_io.keys():
            interface_info = {
                'name': interface_name,
                'bytes_sent': format_bytes(net_io[interface_name].bytes_sent),
                'bytes_recv': format_bytes(net_io[interface_name].bytes_recv),
                'packets_sent': net_io[interface_name].packets_sent,
                'packets_recv': net_io[interface_name].packets_recv,
                'errors_in': net_io[interface_name].errin,
                'errors_out': net_io[interface_name].errout,
                'drops_in': net_io[interface_name].dropin,
                'drops_out': net_io[interface_name].dropout,
            }
            
            # Add IP addresses
            if interface_name in net_if_addrs:
                addresses = []
                for addr in net_if_addrs[interface_name]:
                    if addr.family == socket.AF_INET:  # IPv4
                        addresses.append({
                            'family': 'IPv4',
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                    elif addr.family == socket.AF_INET6:  # IPv6
                        addresses.append({
                            'family': 'IPv6',
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                interface_info['addresses'] = addresses
            
            # Add interface status
            if interface_name in net_if_stats:
                stats = net_if_stats[interface_name]
                interface_info['is_up'] = stats.isup
                interface_info['duplex'] = stats.duplex.name if hasattr(stats.duplex, 'name') else str(stats.duplex)
                interface_info['speed'] = stats.speed
                interface_info['mtu'] = stats.mtu
            
            interfaces[interface_name] = interface_info
        
        return interfaces
    
    except Exception as e:
        return {'error': str(e)}


def format_bytes(bytes_value):
    """Format bytes to human readable format"""
    try:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    except:
        return "0 B"


def run_command(command, shell=False):
    """Safely run system commands"""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Command timed out'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_nftables_status():
    """Get current nftables status"""
    try:
        result = run_command(['nft', 'list', 'ruleset'])
        if result['success']:
            return {
                'active': True,
                'rules_count': len([line for line in result['stdout'].split('\n') if line.strip() and not line.strip().startswith('#')]),
                'config': result['stdout']
            }
        else:
            return {
                'active': False,
                'error': result.get('stderr', 'Unknown error')
            }
    except Exception as e:
        return {
            'active': False,
            'error': str(e)
        }


def get_strongswan_status():
    """Get StrongSwan VPN status"""
    try:
        # Check if strongswan service is running
        result = run_command(['systemctl', 'is-active', 'strongswan'])
        service_active = result['success'] and result['stdout'].strip() == 'active'
        
        # Get connection status
        connections = []
        if service_active:
            conn_result = run_command(['ipsec', 'status'])
            if conn_result['success']:
                # Parse connection status (simplified)
                for line in conn_result['stdout'].split('\n'):
                    if 'ESTABLISHED' in line or 'CONNECTING' in line:
                        connections.append(line.strip())
        
        return {
            'service_active': service_active,
            'connections': connections,
            'connection_count': len(connections)
        }
    except Exception as e:
        return {
            'service_active': False,
            'error': str(e)
        }


def check_system_health():
    """Perform system health checks"""
    health_status = {
        'overall': 'healthy',
        'checks': []
    }
    
    try:
        # Check CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        if cpu_usage > 90:
            health_status['checks'].append({
                'name': 'CPU Usage',
                'status': 'critical',
                'message': f'High CPU usage: {cpu_usage}%'
            })
            health_status['overall'] = 'critical'
        elif cpu_usage > 70:
            health_status['checks'].append({
                'name': 'CPU Usage',
                'status': 'warning',
                'message': f'Elevated CPU usage: {cpu_usage}%'
            })
            if health_status['overall'] == 'healthy':
                health_status['overall'] = 'warning'
        else:
            health_status['checks'].append({
                'name': 'CPU Usage',
                'status': 'healthy',
                'message': f'CPU usage normal: {cpu_usage}%'
            })
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            health_status['checks'].append({
                'name': 'Memory Usage',
                'status': 'critical',
                'message': f'High memory usage: {memory.percent}%'
            })
            health_status['overall'] = 'critical'
        elif memory.percent > 80:
            health_status['checks'].append({
                'name': 'Memory Usage',
                'status': 'warning',
                'message': f'Elevated memory usage: {memory.percent}%'
            })
            if health_status['overall'] == 'healthy':
                health_status['overall'] = 'warning'
        else:
            health_status['checks'].append({
                'name': 'Memory Usage',
                'status': 'healthy',
                'message': f'Memory usage normal: {memory.percent}%'
            })
        
        # Check disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        if disk_percent > 95:
            health_status['checks'].append({
                'name': 'Disk Usage',
                'status': 'critical',
                'message': f'Disk nearly full: {disk_percent:.1f}%'
            })
            health_status['overall'] = 'critical'
        elif disk_percent > 85:
            health_status['checks'].append({
                'name': 'Disk Usage',
                'status': 'warning',
                'message': f'Disk usage high: {disk_percent:.1f}%'
            })
            if health_status['overall'] == 'healthy':
                health_status['overall'] = 'warning'
        else:
            health_status['checks'].append({
                'name': 'Disk Usage',
                'status': 'healthy',
                'message': f'Disk usage normal: {disk_percent:.1f}%'
            })
        
        # Check essential services
        essential_services = ['postgresql', 'redis', 'nginx', 'nftables']
        for service in essential_services:
            result = run_command(['systemctl', 'is-active', service])
            if result['success'] and result['stdout'].strip() == 'active':
                health_status['checks'].append({
                    'name': f'{service.title()} Service',
                    'status': 'healthy',
                    'message': f'{service} is running'
                })
            else:
                health_status['checks'].append({
                    'name': f'{service.title()} Service',
                    'status': 'critical',
                    'message': f'{service} is not running'
                })
                health_status['overall'] = 'critical'
    
    except Exception as e:
        health_status['checks'].append({
            'name': 'Health Check',
            'status': 'error',
            'message': f'Error performing health check: {str(e)}'
        })
        health_status['overall'] = 'error'
    
    return health_status