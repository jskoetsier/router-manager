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
            # If table doesn't exist, that's normal - NAT is just not configured
            if "No such file or directory" in result.get("stderr", "") or \
               "does not exist" in result.get("stderr", ""):
                return {"nat_enabled": False, "nat_rules": ""}
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
        result = run_command(["/usr/bin/sudo", "/sbin/ip", "link", "show"])
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
            # Handle container-style interface names like eth0@if35
            # For ip addr command, we need to use just the base name (eth0)
            query_name = interface_name.split('@')[0] if '@' in interface_name else interface_name

            result = run_command(["/usr/bin/sudo", "/sbin/ip", "addr", "show", query_name])
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


def parse_route_line(route_line):
    """Parse a single route line into structured data"""
    parts = route_line.split()

    route_info = {
        "destination": "-",
        "gateway": "Direct",
        "interface": "-",
        "protocol": "-",
        "metric": "-",
        "full_route": route_line
    }

    # Parse destination
    if "default" in route_line:
        route_info["destination"] = "Default"
    elif "/" in parts[0] if parts else False:
        route_info["destination"] = parts[0]

    # Parse parts
    for i, part in enumerate(parts):
        if part == "via" and i + 1 < len(parts):
            route_info["gateway"] = parts[i + 1]
        elif part == "dev" and i + 1 < len(parts):
            route_info["interface"] = parts[i + 1]
        elif part == "proto" and i + 1 < len(parts):
            route_info["protocol"] = parts[i + 1]
        elif part == "metric" and i + 1 < len(parts):
            route_info["metric"] = parts[i + 1]

    return route_info


def get_routing_table():
    """Get current routing table"""
    try:
        # Get IPv4 routes
        result = run_command(["/usr/bin/sudo", "/sbin/ip", "route", "show"])
        ipv4_routes = []

        if result["success"]:
            for line in result["stdout"].split("\n"):
                if line.strip():
                    parsed_route = parse_route_line(line.strip())
                    ipv4_routes.append(parsed_route)

        # Get IPv6 routes
        result = run_command(["/usr/bin/sudo", "/sbin/ip", "-6", "route", "show"])
        ipv6_routes = []

        if result["success"]:
            for line in result["stdout"].split("\n"):
                if line.strip():
                    parsed_route = parse_route_line(line.strip())
                    ipv6_routes.append(parsed_route)

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


def create_nftables_rule(rule_data):
    """Create a new nftables rule from model data"""
    try:
        # Ensure filter table exists
        result = run_command(["/usr/bin/sudo", "/usr/sbin/nft", "add", "table", "ip", "filter"])

        # Ensure input chain exists
        result = run_command([
            "/usr/bin/sudo", "/usr/sbin/nft", "add", "chain", "ip", "filter", "input",
            "{", "type", "filter", "hook", "input", "priority", "filter;", "policy", "accept;", "}"
        ])

        # Ensure forward chain exists
        result = run_command([
            "/usr/bin/sudo", "/usr/sbin/nft", "add", "chain", "ip", "filter", "forward",
            "{", "type", "filter", "hook", "forward", "priority", "filter;", "policy", "accept;", "}"
        ])

        # Build the nftables rule
        rule_parts = ["add", "rule", "ip", "filter"]

        # Determine chain based on rule type
        if rule_data.get('source_ip') and not rule_data.get('destination_ip'):
            chain = "input"  # Traffic coming to this machine
        elif rule_data.get('destination_ip') and not rule_data.get('source_ip'):
            chain = "forward"  # Traffic being forwarded
        else:
            chain = "input"  # Default to input

        rule_parts.append(chain)

        # Add protocol
        protocol = rule_data.get('protocol', 'tcp')
        if protocol != 'all':
            rule_parts.extend([protocol])

        # Add source IP if specified
        source_ip = rule_data.get('source_ip')
        if source_ip:
            if '/' in source_ip:
                rule_parts.extend(["ip", "saddr", source_ip])
            else:
                rule_parts.extend(["ip", "saddr", source_ip])

        # Add source port if specified
        source_port = rule_data.get('source_port')
        if source_port and protocol in ['tcp', 'udp']:
            rule_parts.extend(["sport", str(source_port)])

        # Add destination IP if specified
        dest_ip = rule_data.get('destination_ip')
        if dest_ip:
            if '/' in dest_ip:
                rule_parts.extend(["ip", "daddr", dest_ip])
            else:
                rule_parts.extend(["ip", "daddr", dest_ip])

        # Add destination port if specified
        dest_port = rule_data.get('destination_port')
        if dest_port and protocol in ['tcp', 'udp']:
            rule_parts.extend(["dport", str(dest_port)])

        # Add action
        action = rule_data.get('action', 'accept')
        rule_parts.append(action)

        # Add comment with rule name
        rule_name = rule_data.get('name', 'unnamed')
        rule_parts.extend(["comment", f'"{rule_name}"'])

        # Execute the nftables command
        result = run_command(["/usr/bin/sudo", "/usr/sbin/nft"] + rule_parts)

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


def create_port_forward_rule(port_forward_data):
    """Create a new port forwarding rule"""
    try:
        external_port = port_forward_data.get('external_port')
        internal_ip = port_forward_data.get('internal_ip')
        internal_port = port_forward_data.get('internal_port')
        protocol = port_forward_data.get('protocol', 'tcp')
        name = port_forward_data.get('name', 'unnamed')

        # Ensure nat table exists
        result = run_command(["/usr/bin/sudo", "/usr/sbin/nft", "add", "table", "ip", "nat"])

        # Ensure prerouting chain exists
        result = run_command([
            "/usr/bin/sudo", "/usr/sbin/nft", "add", "chain", "ip", "nat", "prerouting",
            "{", "type", "nat", "hook", "prerouting", "priority", "dstnat;", "}"
        ])

        # Add DNAT rule for port forwarding
        dnat_rule = [
            "/usr/bin/sudo", "/usr/sbin/nft", "add", "rule", "ip", "nat", "prerouting",
            protocol, "dport", str(external_port),
            "dnat", "to", f"{internal_ip}:{internal_port}",
            "comment", f'"{name}"'
        ]

        result = run_command(dnat_rule)
        if not result['success']:
            return result

        # Ensure filter table and forward chain exist for allowing the forwarded traffic
        result = run_command(["/usr/bin/sudo", "/usr/sbin/nft", "add", "table", "ip", "filter"])

        result = run_command([
            "/usr/bin/sudo", "/usr/sbin/nft", "add", "chain", "ip", "filter", "forward",
            "{", "type", "filter", "hook", "forward", "priority", "filter;", "policy", "accept;", "}"
        ])

        # Add forward rule to allow the traffic
        forward_rule = [
            "/usr/bin/sudo", "/usr/sbin/nft", "add", "rule", "ip", "filter", "forward",
            "ip", "daddr", internal_ip, protocol, "dport", str(internal_port),
            "accept", "comment", f'"{name}_forward"'
        ]

        result = run_command(forward_rule)

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_nftables_rules():
    """Parse nftables rules into structured data"""
    try:
        result = run_command(["/usr/bin/sudo", "/usr/sbin/nft", "list", "ruleset"])
        if not result["success"]:
            return {"rules": [], "error": result.get("error")}

        rules = []
        current_table = None
        current_chain = None

        for line in result["stdout"].split("\n"):
            line = line.strip()

            # Parse table declarations
            if line.startswith("table "):
                parts = line.split()
                if len(parts) >= 3:
                    current_table = {"family": parts[1], "name": parts[2], "chains": []}

            # Parse chain declarations
            elif line.startswith("chain ") and current_table:
                parts = line.split()
                if len(parts) >= 2:
                    current_chain = {"name": parts[1], "rules": []}
                    current_table["chains"].append(current_chain)

            # Parse individual rules
            elif current_chain and line and not line.startswith("#") and not line in ["{", "}"]:
                # Extract comment if present
                comment = ""
                if "comment" in line:
                    comment_match = re.search(r'comment "([^"]*)"', line)
                    if comment_match:
                        comment = comment_match.group(1)

                rule_info = {
                    "table": current_table["family"] + " " + current_table["name"] if current_table else "",
                    "chain": current_chain["name"],
                    "rule": line,
                    "comment": comment
                }
                current_chain["rules"].append(rule_info)
                rules.append(rule_info)

        return {"rules": rules, "error": None}

    except Exception as e:
        return {"rules": [], "error": str(e)}


def add_static_route(destination, gateway, interface, metric=100):
    """Add a static route to the system"""
    try:
        # Build the route command
        if destination.lower() == 'default':
            cmd = ["/usr/bin/sudo", "/sbin/ip", "route", "add", "default"]
        else:
            cmd = ["/usr/bin/sudo", "/sbin/ip", "route", "add", destination]
        
        # Add gateway if specified
        if gateway:
            cmd.extend(["via", gateway])
        
        # Add interface if specified
        if interface:
            cmd.extend(["dev", interface])
        
        # Add metric
        if metric:
            cmd.extend(["metric", str(metric)])
        
        result = run_command(cmd)
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_static_route(destination, gateway=None, interface=None):
    """Delete a static route from the system"""
    try:
        # Build the route command
        if destination.lower() == 'default':
            cmd = ["/usr/bin/sudo", "/sbin/ip", "route", "del", "default"]
        else:
            cmd = ["/usr/bin/sudo", "/sbin/ip", "route", "del", destination]
        
        # Add gateway if specified
        if gateway:
            cmd.extend(["via", gateway])
        
        # Add interface if specified
        if interface:
            cmd.extend(["dev", interface])
        
        result = run_command(cmd)
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def make_route_persistent(destination, gateway, interface, metric=100):
    """Make a route persistent by adding it to network scripts"""
    try:
        # For Rocky Linux/RHEL systems, we'll create a route file
        # This is a simplified approach - production systems may need more sophisticated handling
        
        route_file = f"/etc/sysconfig/network-scripts/route-{interface}"
        
        # Create route entry
        if destination.lower() == 'default':
            route_entry = f"default via {gateway} dev {interface} metric {metric}\n"
        else:
            route_entry = f"{destination} via {gateway} dev {interface} metric {metric}\n"
        
        # Use a simple approach to add the route
        script = f"""#!/bin/bash
# Add route to persistent configuration
echo "{route_entry.strip()}" >> {route_file}
"""
        
        # Write and execute the script
        with open("/tmp/add_route.sh", "w") as f:
            f.write(script)
        os.chmod("/tmp/add_route.sh", 0o755)
        
        result = run_command(["/usr/bin/sudo", "/bin/bash", "/tmp/add_route.sh"])
        
        # Clean up
        try:
            os.remove("/tmp/add_route.sh")
        except:
            pass
        
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def remove_persistent_route(destination, interface):
    """Remove a persistent route from network scripts"""
    try:
        route_file = f"/etc/sysconfig/network-scripts/route-{interface}"
        
        # Create a script to remove the route
        script = f"""#!/bin/bash
# Remove route from persistent configuration
if [ -f "{route_file}" ]; then
    # Create backup
    cp {route_file} {route_file}.bak 2>/dev/null || true
    # Remove the specific route
    grep -v "{destination}" {route_file} > {route_file}.tmp 2>/dev/null || touch {route_file}.tmp
    mv {route_file}.tmp {route_file}
fi
"""
        
        # Write and execute the script
        with open("/tmp/remove_route.sh", "w") as f:
            f.write(script)
        os.chmod("/tmp/remove_route.sh", 0o755)
        
        result = run_command(["/usr/bin/sudo", "/bin/bash", "/tmp/remove_route.sh"])
        
        # Clean up
        try:
            os.remove("/tmp/remove_route.sh")
        except:
            pass
        
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}
