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
        # Get tunnel status using swanctl
        result = subprocess.run(['sudo', 'swanctl', '--list-sas'], 
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
                            'protocol': 'IKEv2' if 'IKEv2' in status_part else 'IKE'
                        }
                        tunnels.append(current_tunnel)
                
                elif current_tunnel and ('bytes_i' in line or 'bytes_o' in line):
                    # Parse traffic statistics
                    if 'bytes_i' in line:
                        try:
                            current_tunnel['bytes_in'] = line.split('bytes_i')[1].split(',')[0].strip()
                        except:
                            pass
                    if 'bytes_o' in line:
                        try:
                            current_tunnel['bytes_out'] = line.split('bytes_o')[1].split(',')[0].strip()
                        except:
                            pass
        
        # Also get configured connections that might not be active
        result_conns = subprocess.run(['sudo', 'swanctl', '--list-conns'], 
                                    capture_output=True, text=True, timeout=10)
        
        if result_conns.returncode == 0:
            active_names = [t['name'] for t in tunnels]
            lines = result_conns.stdout.split('\n')
            
            for line in lines:
                if ':' in line and 'IKEv' in line:
                    name = line.split(':')[0].strip()
                    if name not in active_names:
                        tunnels.append({
                            'name': name,
                            'status': 'CONFIGURED',
                            'remote_ip': 'Not connected',
                            'type': 'IPSec',
                            'protocol': 'IKEv2' if 'IKEv2' in line else 'IKE',
                            'bytes_in': '0',
                            'bytes_out': '0'
                        })
        
    except Exception as e:
        # Fallback with dummy data to show the interface works
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