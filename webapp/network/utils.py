"""
Network management utilities
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


def get_ip_forwarding_status():
    """Get current IP forwarding status"""
    try:
        # Check IPv4 forwarding
        result = run_command(
            ["/usr/bin/sudo", "/usr/sbin/sysctl", "net.ipv4.ip_forward"]
        )
        if result["success"]:
            ipv4_forward = "1" in result["stdout"]
        else:
            ipv4_forward = False

        # Check IPv6 forwarding
        result = run_command(
            ["/usr/bin/sudo", "/usr/sbin/sysctl", "net.ipv6.conf.all.forwarding"]
        )
        if result["success"]:
            ipv6_forward = "1" in result["stdout"]
        else:
            ipv6_forward = False

        return {"ipv4_forwarding": ipv4_forward, "ipv6_forwarding": ipv6_forward}
    except Exception as e:
        return {"ipv4_forwarding": False, "ipv6_forwarding": False, "error": str(e)}


def set_ip_forwarding(ipv4_enabled=True, ipv6_enabled=True, permanent=True):
    """Enable or disable IP forwarding"""
    results = []

    # Set IPv4 forwarding
    ipv4_value = "1" if ipv4_enabled else "0"
    result = run_command(
        ["/usr/bin/sudo", "/usr/sbin/sysctl", "-w", f"net.ipv4.ip_forward={ipv4_value}"]
    )
    results.append(("IPv4 forwarding", result["success"], result.get("error", "")))

    # Set IPv6 forwarding
    ipv6_value = "1" if ipv6_enabled else "0"
    result = run_command(
        [
            "/usr/bin/sudo",
            "/usr/sbin/sysctl",
            "-w",
            f"net.ipv6.conf.all.forwarding={ipv6_value}",
        ]
    )
    results.append(("IPv6 forwarding", result["success"], result.get("error", "")))

    # Make permanent if requested - use a simpler approach
    if permanent:
        try:
            # Use a simpler approach that works with our sudoers configuration
            # First backup the current file
            backup_result = run_command(
                ["/usr/bin/sudo", "/bin/cp", "/etc/sysctl.conf", "/etc/sysctl.conf.bak"]
            )

            # Create new content for sysctl.conf
            update_script = f"""#!/bin/bash
# Remove existing IP forwarding entries and add new ones
grep -v "net.ipv4.ip_forward" /etc/sysctl.conf.bak | grep -v "net.ipv6.conf.all.forwarding" > /tmp/sysctl_new.conf
echo "net.ipv4.ip_forward = {ipv4_value}" >> /tmp/sysctl_new.conf
echo "net.ipv6.conf.all.forwarding = {ipv6_value}" >> /tmp/sysctl_new.conf
cp /tmp/sysctl_new.conf /etc/sysctl.conf
rm /tmp/sysctl_new.conf
"""

            # Write and execute the update script
            with open("/tmp/update_sysctl.sh", "w") as f:
                f.write(update_script)
            os.chmod("/tmp/update_sysctl.sh", 0o755)

            result = run_command(
                ["/usr/bin/sudo", "/bin/bash", "/tmp/update_sysctl.sh"]
            )

            # Clean up
            try:
                os.remove("/tmp/update_sysctl.sh")
            except:
                pass

            results.append(
                ("Permanent configuration", result["success"], result.get("error", ""))
            )

        except Exception as e:
            results.append(("Permanent configuration", False, str(e)))

    return results


def get_nat_status():
    """Get current NAT status from nftables"""
    try:
        result = run_command(
            ["/usr/bin/sudo", "/usr/sbin/nft", "list", "table", "ip", "nat"]
        )
        if result["success"]:
            # Check if NAT table exists and has rules
            nat_enabled = "chain postrouting" in result["stdout"]
            return {"nat_enabled": nat_enabled, "nat_rules": result["stdout"]}
        else:
            return {
                "nat_enabled": False,
                "nat_rules": "",
                "error": result.get("error", "NAT table not found"),
            }
    except Exception as e:
        return {"nat_enabled": False, "nat_rules": "", "error": str(e)}


def configure_basic_nat(interface="eth0", enabled=True):
    """Configure basic NAT masquerading"""
    results = []

    if enabled:
        # Create NAT table if it doesn't exist
        result = run_command(
            ["/usr/bin/sudo", "/usr/sbin/nft", "add", "table", "ip", "nat"]
        )
        # Don't check success as table might already exist

        # Create postrouting chain
        result = run_command(
            [
                "/usr/bin/sudo",
                "/usr/sbin/nft",
                "add",
                "chain",
                "ip",
                "nat",
                "postrouting",
                "{",
                "type",
                "nat",
                "hook",
                "postrouting",
                "priority",
                "srcnat;",
                "}",
            ]
        )
        # Don't check success as chain might already exist

        # Add masquerade rule for the interface
        result = run_command(
            [
                "/usr/bin/sudo",
                "/usr/sbin/nft",
                "add",
                "rule",
                "ip",
                "nat",
                "postrouting",
                "oifname",
                interface,
                "masquerade",
            ]
        )
        results.append(
            ("NAT masquerade rule", result["success"], result.get("error", ""))
        )

    else:
        # Remove NAT table (this removes all NAT rules)
        result = run_command(
            ["/usr/bin/sudo", "/usr/sbin/nft", "delete", "table", "ip", "nat"]
        )
        results.append(("Remove NAT table", result["success"], result.get("error", "")))

    return results


def get_network_interfaces():
    """Get detailed network interface information"""
    try:
        # Get interface list
        result = run_command(["ip", "link", "show"])
        if not result["success"]:
            return {}

        interfaces = {}

        # Parse ip link output
        for line in result["stdout"].split("\n"):
            if re.match(r"^\d+:", line):
                parts = line.split()
                if len(parts) >= 2:
                    # Extract interface name
                    interface_name = parts[1].rstrip(":")

                    # Skip virtual interfaces we don't want to show
                    if interface_name.startswith(("veth", "docker", "br-")):
                        continue

                    # Determine interface state
                    state = "UP" if "UP" in line else "DOWN"

                    interfaces[interface_name] = {
                        "name": interface_name,
                        "state": state,
                        "ip_addresses": [],
                        "type": "ethernet",  # Default type
                    }

        # Get IP addresses for each interface
        for interface_name in interfaces.keys():
            result = run_command(["ip", "addr", "show", interface_name])
            if result["success"]:
                for line in result["stdout"].split("\n"):
                    if "inet " in line and not line.strip().startswith("inet 127."):
                        # Extract IP address
                        ip_match = re.search(r"inet ([0-9.]+/[0-9]+)", line)
                        if ip_match:
                            interfaces[interface_name]["ip_addresses"].append(
                                {"family": "IPv4", "address": ip_match.group(1)}
                            )
                    elif "inet6 " in line and not "fe80:" in line:
                        # Extract IPv6 address (skip link-local)
                        ip_match = re.search(r"inet6 ([0-9a-f:]+/[0-9]+)", line)
                        if ip_match:
                            interfaces[interface_name]["ip_addresses"].append(
                                {"family": "IPv6", "address": ip_match.group(1)}
                            )

        return interfaces

    except Exception as e:
        return {"error": str(e)}


def get_routing_table():
    """Get current routing table"""
    try:
        # Get IPv4 routes
        result = run_command(["ip", "route", "show"])
        ipv4_routes = []

        if result["success"]:
            for line in result["stdout"].split("\n"):
                if line.strip():
                    ipv4_routes.append(line.strip())

        # Get IPv6 routes
        result = run_command(["ip", "-6", "route", "show"])
        ipv6_routes = []

        if result["success"]:
            for line in result["stdout"].split("\n"):
                if line.strip():
                    ipv6_routes.append(line.strip())

        return {"ipv4_routes": ipv4_routes, "ipv6_routes": ipv6_routes}

    except Exception as e:
        return {"error": str(e)}


def get_nftables_rules():
    """Get current nftables rules"""
    try:
        result = run_command(["/usr/bin/sudo", "/usr/sbin/nft", "list", "ruleset"])
        if result["success"]:
            return {
                "rules": result["stdout"],
                "rule_count": len(
                    [
                        line
                        for line in result["stdout"].split("\n")
                        if line.strip() and not line.strip().startswith("#")
                    ]
                ),
            }
        else:
            return {
                "rules": "",
                "rule_count": 0,
                "error": result.get("error", "Failed to get nftables rules"),
            }
    except Exception as e:
        return {"rules": "", "rule_count": 0, "error": str(e)}


def validate_ip_address(ip):
    """Validate IP address format"""
    import ipaddress

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_cidr(cidr):
    """Validate CIDR notation"""
    import ipaddress

    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except ValueError:
        return False
