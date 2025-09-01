"""
VPN utility functions for Router Manager
"""

import subprocess
import re
import json
from datetime import datetime


def get_vpn_status():
    """
    Get overall VPN service status
    """
    try:
        # Check StrongSwan service status
        result = subprocess.run(['systemctl', 'is-active', 'strongswan'],
                              capture_output=True, text=True)

        service_status = result.stdout.strip()

        return {
            'service_running': service_status == 'active',
            'service_status': service_status,
            'last_checked': datetime.now()
        }
    except Exception as e:
        return {
            'service_running': False,
            'service_status': f'Error: {e}',
            'last_checked': datetime.now()
        }


def restart_vpn_service():
    """
    Restart the VPN service
    """
    try:
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'strongswan'],
                              capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception:
        return False


def get_connected_clients():
    """
    Get list of currently connected VPN clients
    """
    try:
        # This is a placeholder - implement based on your VPN solution
        # For OpenVPN, you might read from status files
        # For WireGuard, you might use 'wg show'
        return []
    except Exception as e:
        return []


def get_ipsec_tunnels():
    """
    Get IPSec tunnel status from swanctl
    """
    tunnels = []
    try:
        # First, check if strongswan is installed and running
        service_check = subprocess.run(['systemctl', 'is-active', 'strongswan'],
                                     capture_output=True, text=True, timeout=5)

        if service_check.returncode != 0:
            # StrongSwan not active, return empty list or error
            tunnels.append({
                'name': 'StrongSwan Service',
                'status': 'INACTIVE',
                'remote_ip': 'Service not running',
                'type': 'IPSec',
                'protocol': 'N/A',
                'bytes_in': '0',
                'bytes_out': '0'
            })
            return tunnels

        # Check if swanctl command exists
        swanctl_check = subprocess.run(['which', 'swanctl'],
                                     capture_output=True, text=True, timeout=5)

        if swanctl_check.returncode != 0:
            # swanctl not found, try alternative commands
            # Try with full path
            swanctl_path = None
            for path in ['/usr/sbin/swanctl', '/usr/local/sbin/swanctl', '/sbin/swanctl']:
                if subprocess.run(['test', '-x', path], capture_output=True).returncode == 0:
                    swanctl_path = path
                    break

            if not swanctl_path:
                tunnels.append({
                    'name': 'SwanCTL Command',
                    'status': 'NOT_FOUND',
                    'remote_ip': 'swanctl command not found',
                    'type': 'IPSec',
                    'protocol': 'N/A',
                    'bytes_in': '0',
                    'bytes_out': '0'
                })
                return tunnels
        else:
            swanctl_path = 'swanctl'

        # Get tunnel status using swanctl
        result = subprocess.run(['sudo', swanctl_path, '--list-sas'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            lines = result.stdout.split('\n')
            current_tunnel = {}

            for line in lines:
                line = line.strip()
                if ':' in line and ('ESTABLISHED' in line or 'CONNECTING' in line or 'INSTALLED' in line):
                    # Parse tunnel name and status
                    parts = line.split(':')
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        status_part = parts[1].strip()

                        if 'ESTABLISHED' in status_part:
                            status = 'ESTABLISHED'
                        elif 'CONNECTING' in status_part:
                            status = 'CONNECTING'
                        elif 'INSTALLED' in status_part:
                            status = 'INSTALLED'
                        else:
                            status = 'UNKNOWN'

                        # Extract remote IP if available
                        remote_ip = 'Unknown'
                        if 'to ' in status_part:
                            try:
                                remote_ip = status_part.split('to ')[1].split()[0]
                            except:
                                pass

                        current_tunnel = {
                            'name': name,
                            'status': status,
                            'remote_ip': remote_ip,
                            'type': 'IPSec',
                            'protocol': 'IKEv2' if 'IKEv2' in status_part else 'IKE',
                            'bytes_in': '0',
                            'bytes_out': '0'
                        }
                        tunnels.append(current_tunnel)

                elif current_tunnel and ('bytes_i' in line or 'bytes_o' in line):
                    # Parse traffic statistics - improve parsing for different formats
                    if 'bytes_i' in line:
                        try:
                            # Handle different formats like "bytes_i=1234" or "bytes_i: 1234"
                            if '=' in line:
                                bytes_value = line.split('bytes_i=')[1].split(',')[0].split()[0].strip()
                            else:
                                bytes_value = line.split('bytes_i')[1].split(',')[0].strip().lstrip(':').strip()
                            current_tunnel['bytes_in'] = bytes_value
                        except:
                            current_tunnel['bytes_in'] = '0'
                    if 'bytes_o' in line:
                        try:
                            # Handle different formats
                            if '=' in line:
                                bytes_value = line.split('bytes_o=')[1].split(',')[0].split()[0].strip()
                            else:
                                bytes_value = line.split('bytes_o')[1].split(',')[0].strip().lstrip(':').strip()
                            current_tunnel['bytes_out'] = bytes_value
                        except:
                            current_tunnel['bytes_out'] = '0'

        # Also get configured connections that might not be active
        try:
            result_conns = subprocess.run(['sudo', swanctl_path, '--list-conns'],
                                        capture_output=True, text=True, timeout=10)

            if result_conns.returncode == 0:
                active_names = [t['name'] for t in tunnels]
                lines = result_conns.stdout.split('\n')

                for line in lines:
                    if ':' in line and ('IKEv' in line or 'remote_addrs' in line):
                        # Handle different swanctl output formats
                        name = line.split(':')[0].strip()
                        if name and name not in active_names and not name.startswith(' '):
                            tunnels.append({
                                'name': name,
                                'status': 'CONFIGURED',
                                'remote_ip': 'Not connected',
                                'type': 'IPSec',
                                'protocol': 'IKEv2' if 'IKEv2' in line else 'IKE',
                                'bytes_in': '0',
                                'bytes_out': '0'
                            })
        except:
            # If listing connections fails, just continue with SAs
            pass

        # If no tunnels found but no error, add informational entry
        if not tunnels:
            tunnels.append({
                'name': 'No VPN Tunnels',
                'status': 'NONE',
                'remote_ip': 'No tunnels configured',
                'type': 'IPSec',
                'protocol': 'N/A',
                'bytes_in': '0',
                'bytes_out': '0'
            })

    except subprocess.TimeoutExpired:
        tunnels.append({
            'name': 'Command Timeout',
            'status': 'TIMEOUT',
            'remote_ip': 'swanctl command timed out',
            'type': 'IPSec',
            'protocol': 'N/A',
            'bytes_in': '0',
            'bytes_out': '0'
        })
    except Exception as e:
        # Fallback with error information
        tunnels.append({
            'name': 'Error retrieving tunnels',
            'status': 'ERROR',
            'remote_ip': str(e),
            'type': 'IPSec',
            'protocol': 'N/A',
            'bytes_in': '0',
            'bytes_out': '0'
        })

    return tunnels


def restart_ipsec_service():
    """
    Restart IPSec service
    """
    try:
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'strongswan'],
                              capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception:
        return False


def initiate_tunnel(tunnel_name):
    """
    Initiate an IPSec tunnel
    """
    try:
        result = subprocess.run(['sudo', 'swanctl', '--initiate', '--child', tunnel_name],
                              capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def terminate_tunnel(tunnel_name):
    """
    Terminate an IPSec tunnel
    """
    try:
        result = subprocess.run(['sudo', 'swanctl', '--terminate', '--ike', tunnel_name],
                              capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)
