"""
VPN management utilities for StrongSwan IPSec
"""

import os
import re
import subprocess

from django.conf import settings


def run_command(command, shell=False, check_output=True):
    """Run system command safely"""
    try:
        if check_output:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            return {
                "success": True,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        else:
            result = subprocess.run(command, shell=shell, timeout=30, check=True)
            return {"success": True, "returncode": result.returncode}
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "stdout": e.stdout.strip() if e.stdout else "",
            "stderr": e.stderr.strip() if e.stderr else "",
            "returncode": e.returncode,
            "error": str(e),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_strongswan_status():
    """Get StrongSwan service status"""
    try:
        # Check if strongswan service is running
        result = run_command(
            ["/usr/bin/sudo", "/usr/bin/systemctl", "is-active", "strongswan"]
        )
        service_active = result["success"] and result["stdout"].strip() == "active"

        # Get connection status
        connections = []
        if service_active:
            conn_result = run_command(["/usr/bin/sudo", "/usr/sbin/ipsec", "status"])
            if conn_result["success"]:
                # Parse connection status
                for line in conn_result["stdout"].split("\n"):
                    if (
                        "ESTABLISHED" in line
                        or "CONNECTING" in line
                        or "INSTALLED" in line
                    ):
                        connections.append(line.strip())

        return {
            "service_active": service_active,
            "connections": connections,
            "connection_count": len(connections),
        }
    except Exception as e:
        return {"service_active": False, "error": str(e)}


def create_ipsec_config(
    tunnel_name, local_ip, remote_ip, local_subnet, remote_subnet, psk
):
    """Create IPSec configuration files"""
    try:
        # Create ipsec.conf entry
        ipsec_conf_entry = f"""
conn {tunnel_name}
    left={local_ip}
    leftsubnet={local_subnet}
    right={remote_ip}
    rightsubnet={remote_subnet}
    authby=secret
    auto=start
    type=tunnel
    keyexchange=ikev2
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256!
    dpdaction=restart
    dpddelay=30s
    dpdtimeout=120s
"""

        # Create ipsec.secrets entry
        ipsec_secrets_entry = f'{local_ip} {remote_ip} : PSK "{psk}"\n'

        return {
            "success": True,
            "ipsec_conf": ipsec_conf_entry,
            "ipsec_secrets": ipsec_secrets_entry,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def add_tunnel_to_strongswan(tunnel_config):
    """Add tunnel configuration to StrongSwan"""
    try:
        results = []

        # Backup existing configuration
        result = run_command(
            [
                "/usr/bin/sudo",
                "/usr/bin/cp",
                "/etc/strongswan/ipsec.conf",
                "/etc/strongswan/ipsec.conf.bak",
            ]
        )

        # Append new tunnel configuration to ipsec.conf
        script_content = f"""#!/bin/bash
echo '{tunnel_config["ipsec_conf"]}' >> /etc/strongswan/ipsec.conf
"""

        script_path = "/tmp/add_ipsec_config.sh"
        with open(script_path, "w") as f:
            f.write(script_content)

        os.chmod(script_path, 0o755)
        result = run_command(["/usr/bin/sudo", "/bin/bash", script_path])
        results.append(
            ("Add ipsec.conf entry", result["success"], result.get("error", ""))
        )

        # Add PSK to ipsec.secrets
        secrets_script = f"""#!/bin/bash
echo '{tunnel_config["ipsec_secrets"]}' >> /etc/strongswan/ipsec.secrets
"""

        secrets_script_path = "/tmp/add_ipsec_secrets.sh"
        with open(secrets_script_path, "w") as f:
            f.write(secrets_script)

        os.chmod(secrets_script_path, 0o755)
        result = run_command(["/usr/bin/sudo", "/bin/bash", secrets_script_path])
        results.append(
            ("Add ipsec.secrets entry", result["success"], result.get("error", ""))
        )

        # Reload StrongSwan configuration
        result = run_command(["/usr/bin/sudo", "/usr/sbin/ipsec", "reload"])
        results.append(
            ("Reload StrongSwan", result["success"], result.get("error", ""))
        )

        # Start the tunnel
        result = run_command(
            [
                "/usr/bin/sudo",
                "/usr/sbin/ipsec",
                "up",
                tunnel_config.get("name", "tunnel"),
            ]
        )
        results.append(("Start tunnel", result["success"], result.get("error", "")))

        # Clean up temporary files
        for temp_file in [script_path, secrets_script_path]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        return results

    except Exception as e:
        return [("Add tunnel configuration", False, str(e))]


def remove_tunnel_from_strongswan(tunnel_name):
    """Remove tunnel configuration from StrongSwan"""
    try:
        results = []

        # Stop the tunnel first
        result = run_command(["/usr/bin/sudo", "/usr/sbin/ipsec", "down", tunnel_name])
        results.append(("Stop tunnel", result["success"], result.get("error", "")))

        # Remove from ipsec.conf (create a script to do this safely)
        script_content = f"""#!/bin/bash
# Backup current config
cp /etc/strongswan/ipsec.conf /etc/strongswan/ipsec.conf.bak

# Remove tunnel configuration
awk '
BEGIN {{ in_conn = 0 }}
/^conn {tunnel_name}$/ {{ in_conn = 1; next }}
/^conn / && in_conn {{ in_conn = 0 }}
/^$/ && in_conn {{ in_conn = 0 }}
!in_conn {{ print }}
' /etc/strongswan/ipsec.conf.bak > /etc/strongswan/ipsec.conf
"""

        script_path = "/tmp/remove_ipsec_config.sh"
        with open(script_path, "w") as f:
            f.write(script_content)

        os.chmod(script_path, 0o755)
        result = run_command(["/usr/bin/sudo", "/bin/bash", script_path])
        results.append(
            ("Remove ipsec.conf entry", result["success"], result.get("error", ""))
        )

        # Reload StrongSwan configuration
        result = run_command(["/usr/bin/sudo", "/usr/sbin/ipsec", "reload"])
        results.append(
            ("Reload StrongSwan", result["success"], result.get("error", ""))
        )

        # Clean up
        if os.path.exists(script_path):
            os.remove(script_path)

        return results

    except Exception as e:
        return [("Remove tunnel configuration", False, str(e))]


def get_tunnel_status(tunnel_name):
    """Get status of a specific tunnel"""
    try:
        result = run_command(
            ["/usr/bin/sudo", "/usr/sbin/ipsec", "status", tunnel_name]
        )
        if result["success"]:
            status_text = result["stdout"]
            if "ESTABLISHED" in status_text:
                return "connected"
            elif "CONNECTING" in status_text:
                return "connecting"
            else:
                return "disconnected"
        else:
            return "unknown"
    except Exception:
        return "error"


def validate_ip_address(ip):
    """Validate IP address format"""
    import ipaddress

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_subnet(subnet):
    """Validate subnet format (CIDR notation)"""
    import ipaddress

    try:
        ipaddress.ip_network(subnet, strict=False)
        return True
    except ValueError:
        return False


def generate_psk(length=32):
    """Generate a random pre-shared key"""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))
