#!/bin/bash

# IPSec Tunnel Configuration Script for Juniper SRX
# Configures the external server (195.95.177.8) as StrongSwan responder
# for a Juniper SRX running Junos 12.1X46-D40.2 acting as initiator

set -euo pipefail

# Configuration variables
EXTERNAL_SERVER="195.95.177.8"
EXTERNAL_SSH_PORT="22123"
EXTERNAL_USER="root"

# Network configuration - adjust these as needed
EXTERNAL_NETWORK="195.95.177.0/28"           # External server's network
INTERNAL_NETWORK="192.168.100.0/24"          # SRX internal network (adjust as needed)
TUNNEL_EXTERNAL_IP="195.95.177.8"            # External server IP
TUNNEL_INTERNAL_IP="192.168.100.1"           # SRX internal IP (adjust as needed)

# IPSec configuration parameters
IPSEC_PSK="${IPSEC_PSK:-$(openssl rand -base64 32)}"
IPSEC_LIFETIME="28800"
IKE_VERSION="ikev1"  # Junos 12.1X46-D40.2 works better with IKEv1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
LOG_FILE="/tmp/juniper-ipsec-setup-$(date +%Y%m%d-%H%M%S).log"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to test SSH connectivity
test_ssh_connection() {
    local host="$1"
    local port="$2"
    local user="$3"

    print_status "Testing SSH connection to $user@$host:$port..."

    if timeout 10 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$port" "$user@$host" "echo 'Connection successful'" 2>/dev/null; then
        print_success "SSH connection to $user@$host:$port successful"
        return 0
    else
        print_error "Cannot connect to $user@$host:$port"
        return 1
    fi
}

# Function to configure external server as StrongSwan responder
configure_external_server() {
    print_status "Configuring external server as StrongSwan responder..."

    # Create configuration script for external server
    cat > /tmp/external-server-config.sh << 'EOF'
#!/bin/bash

set -e

# Check if StrongSwan is already installed
if command -v strongswan >/dev/null 2>&1 || command -v swanctl >/dev/null 2>&1; then
    echo "StrongSwan is already installed, checking version..."
    strongswan version || swanctl --version || true
else
    # Update system
    echo "Updating system packages..."
    dnf update -y

    # Install required packages
    echo "Installing StrongSwan and related packages..."
    dnf install -y strongswan strongswan-charon strongswan-libipsec nftables
fi

# Enable IP forwarding
echo "Enabling IP forwarding..."
echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-ipsec-juniper.conf
echo 'net.ipv6.conf.all.forwarding = 1' >> /etc/sysctl.d/99-ipsec-juniper.conf
sysctl -p /etc/sysctl.d/99-ipsec-juniper.conf

# Create StrongSwan configuration directory
mkdir -p /etc/swanctl/conf.d
mkdir -p /etc/swanctl/x509
mkdir -p /etc/swanctl/private

# Enable and start services
echo "Enabling services..."
systemctl enable strongswan
systemctl start strongswan

echo "External server configuration completed successfully"
EOF

    # Copy and execute configuration script on external server
    scp -P "$EXTERNAL_SSH_PORT" /tmp/external-server-config.sh "$EXTERNAL_USER@$EXTERNAL_SERVER":/tmp/
    ssh -p "$EXTERNAL_SSH_PORT" "$EXTERNAL_USER@$EXTERNAL_SERVER" "chmod +x /tmp/external-server-config.sh && /tmp/external-server-config.sh"

    print_success "External server configured successfully"
}

# Function to create StrongSwan responder configuration
create_strongswan_config() {
    print_status "Creating StrongSwan responder configuration..."

    # Create swanctl configuration for responder mode
    cat > /tmp/swanctl.conf << EOF
connections {
    juniper-srx {
        version = 1
        local_addrs = ${TUNNEL_EXTERNAL_IP}
        
        # Accept connections from any IP (since SRX is behind NAT)
        remote_addrs = %any
        
        # Responder mode - wait for initiator
        initiator = no
        
        local {
            auth = psk
            id = ${TUNNEL_EXTERNAL_IP}
        }
        
        remote {
            auth = psk
            # Accept any ID from initiator
            id = %any
        }
        
        children {
            juniper-child {
                # External server network
                local_ts = ${EXTERNAL_NETWORK}
                
                # SRX internal network - allow full access
                remote_ts = ${INTERNAL_NETWORK}
                
                # ESP proposals compatible with Juniper SRX 12.1X46-D40.2
                esp_proposals = aes256-sha1-modp1024,aes128-sha1-modp1024,3des-sha1-modp1024
                
                mode = tunnel
                start_action = start
                close_action = restart
                
                # Enable NAT traversal for SRX behind NAT
                if_id_in = 42
                if_id_out = 42
            }
        }
        
        # IKE proposals compatible with Juniper SRX 12.1X46-D40.2
        proposals = aes256-sha1-modp1024,aes128-sha1-modp1024,3des-sha1-modp1024
        
        # Dead Peer Detection - important for NAT traversal
        dpd_delay = 30s
        dpd_timeout = 120s
        
        # Rekey timers
        rekey_time = 4h
        over_time = 10m
        
        # NAT traversal settings
        encap = yes
        
        # Fragmentation for NAT environments
        fragmentation = yes
    }
}

secrets {
    ike-juniper {
        # Use IP-based ID matching
        id-${TUNNEL_EXTERNAL_IP} = "$IPSEC_PSK"
    }
}
EOF

    # Copy configuration to external server
    scp -P "$EXTERNAL_SSH_PORT" /tmp/swanctl.conf "$EXTERNAL_USER@$EXTERNAL_SERVER":/etc/swanctl/

    # Load the configuration
    ssh -p "$EXTERNAL_SSH_PORT" "$EXTERNAL_USER@$EXTERNAL_SERVER" "swanctl --load-all"

    print_success "StrongSwan responder configuration created and loaded"
}

# Function to configure nftables for IPSec and internet routing
configure_nftables() {
    print_status "Configuring nftables for IPSec and internet routing..."

    cat > /tmp/juniper-ipsec-nftables.nft << 'NFTEOF'
#!/usr/sbin/nft -f

flush ruleset

define INTERNAL_NET = INTERNAL_NET_PLACEHOLDER
define EXTERNAL_NET = EXTERNAL_NET_PLACEHOLDER
define INTERNET_IFACE = INTERNET_INTERFACE_PLACEHOLDER

table inet juniper_ipsec {
    chain input {
        type filter hook input priority filter; policy drop;

        # Loopback
        iifname "lo" accept

        # Established connections
        ct state established,related accept

        # SSH
        tcp dport { 22, 22123 } accept

        # IPSec - IKE and ESP
        udp dport { 500, 4500 } accept
        ip protocol esp accept

        # ICMP
        icmp type { echo-request, destination-unreachable, time-exceeded } accept

        # From internal network through tunnel
        ip saddr $INTERNAL_NET accept
        
        # Allow traffic on virtual tunnel interface
        iifname "vti*" accept
    }

    chain forward {
        type filter hook forward priority filter; policy drop;

        # Established connections
        ct state established,related accept

        # Traffic from SRX internal network to internet
        ip saddr $INTERNAL_NET oifname $INTERNET_IFACE accept
        
        # Return traffic from internet to SRX network
        iifname $INTERNET_IFACE ip daddr $INTERNAL_NET ct state established,related accept
        
        # Allow traffic between tunnel interfaces
        iifname "vti*" accept
        oifname "vti*" accept

        # IPSec tunnel traffic
        ipsec in accept
        ipsec out accept
    }

    chain output {
        type filter hook output priority filter; policy accept;
    }
}

table inet juniper_nat {
    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;

        # NAT traffic from SRX network to internet
        ip saddr $INTERNAL_NET oifname $INTERNET_IFACE masquerade
        
        # General internet NAT (for other local traffic)
        oifname $INTERNET_IFACE masquerade
    }
}
NFTEOF

    # Get internet interface and replace placeholders
    INTERNET_INTERFACE=$(ssh -p "$EXTERNAL_SSH_PORT" "$EXTERNAL_USER@$EXTERNAL_SERVER" "ip route | grep '^default' | awk '{print \$5}' | head -1")
    
    sed -i "s/INTERNAL_NET_PLACEHOLDER/$INTERNAL_NETWORK/g" /tmp/juniper-ipsec-nftables.nft
    sed -i "s/EXTERNAL_NET_PLACEHOLDER/$EXTERNAL_NETWORK/g" /tmp/juniper-ipsec-nftables.nft
    sed -i "s/INTERNET_INTERFACE_PLACEHOLDER/$INTERNET_INTERFACE/g" /tmp/juniper-ipsec-nftables.nft

    # Copy and apply nftables configuration
    scp -P "$EXTERNAL_SSH_PORT" /tmp/juniper-ipsec-nftables.nft "$EXTERNAL_USER@$EXTERNAL_SERVER":/etc/nftables/
    ssh -p "$EXTERNAL_SSH_PORT" "$EXTERNAL_USER@$EXTERNAL_SERVER" "nft -f /etc/nftables/juniper-ipsec-nftables.nft"

    print_success "nftables configuration applied"
}

# Function to create Juniper SRX configuration
create_juniper_config() {
    print_status "Creating Juniper SRX configuration..."

    cat > /tmp/juniper-srx-config.txt << EOF
# Juniper SRX Configuration for IPSec Tunnel
# For Junos version 12.1X46-D40.2
# This device acts as the initiator (behind NAT)

# ================================
# IKE Configuration
# ================================

set security ike proposal ike-prop-external authentication-method pre-shared-keys
set security ike proposal ike-prop-external dh-group group2
set security ike proposal ike-prop-external authentication-algorithm sha1
set security ike proposal ike-prop-external encryption-algorithm aes-256-cbc

set security ike policy ike-policy-external mode main
set security ike policy ike-policy-external proposals ike-prop-external
set security ike policy ike-policy-external pre-shared-key ascii-text "$IPSEC_PSK"

set security ike gateway external-gw ike-policy ike-policy-external
set security ike gateway external-gw address ${TUNNEL_EXTERNAL_IP}
set security ike gateway external-gw dead-peer-detection interval 30
set security ike gateway external-gw dead-peer-detection threshold 3
set security ike gateway external-gw nat-keepalive 10
set security ike gateway external-gw external-interface ge-0/0/0
set security ike gateway external-gw version v1-only

# ================================
# IPSec Configuration
# ================================

set security ipsec proposal ipsec-prop-external protocol esp
set security ipsec proposal ipsec-prop-external authentication-algorithm hmac-sha1-96
set security ipsec proposal ipsec-prop-external encryption-algorithm aes-256-cbc

set security ipsec policy ipsec-policy-external perfect-forward-secrecy keys group2
set security ipsec policy ipsec-policy-external proposals ipsec-prop-external

set security ipsec vpn external-tunnel ike gateway external-gw
set security ipsec vpn external-tunnel ike ipsec-policy ipsec-policy-external
set security ipsec vpn external-tunnel bind-interface st0.0

# ================================
# Tunnel Interface Configuration
# ================================

set interfaces st0 unit 0 family inet address 10.0.0.1/30
set interfaces st0 unit 0 family inet mtu 1436

# ================================
# Security Zones
# ================================

set security zones security-zone trust interfaces st0.0
set security zones security-zone trust host-inbound-traffic system-services all
set security zones security-zone trust host-inbound-traffic protocols all

# ================================
# Routing Configuration
# ================================

# Route external network traffic through the tunnel
set routing-options static route ${EXTERNAL_NETWORK} next-hop st0.0

# Default route for internet traffic through tunnel (optional - for full internet routing)
set routing-options static route 0.0.0.0/0 next-hop st0.0 preference 5

# ================================
# Security Policies
# ================================

set security policies from-zone trust to-zone trust policy allow-all match source-address any
set security policies from-zone trust to-zone trust policy allow-all match destination-address any
set security policies from-zone trust to-zone trust policy allow-all match application any
set security policies from-zone trust to-zone trust policy allow-all then permit

# ================================
# NAT Configuration (if needed for local network)
# ================================

# If you have internal hosts that need NAT to access the internet through tunnel
set security nat source rule-set trust-to-untrust from zone trust
set security nat source rule-set trust-to-untrust to zone untrust
set security nat source rule-set trust-to-untrust rule source-nat-rule match source-address 0.0.0.0/0
set security nat source rule-set trust-to-untrust rule source-nat-rule then source-nat interface

# ================================
# Commit and Operational Commands
# ================================

# After applying the configuration, commit it:
commit

# Operational commands for monitoring:
# show security ike security-associations
# show security ipsec security-associations
# show interfaces st0.0
# show route
# ping ${TUNNEL_EXTERNAL_IP} source st0.0

# ================================
# Configuration Notes
# ================================

# 1. Adjust interface names (ge-0/0/0) to match your SRX configuration
# 2. Modify IP addresses and networks to match your environment
# 3. The SRX internal network is configured as ${INTERNAL_NETWORK}
# 4. External server network is ${EXTERNAL_NETWORK}
# 5. Pre-shared key: $IPSEC_PSK

# ================================
# Troubleshooting Commands
# ================================

# show security ike security-associations detail
# show security ipsec security-associations detail
# show log messages | match IKE
# show log messages | match IPSec
# clear security ike security-associations
# clear security ipsec security-associations

EOF

    print_status "Juniper SRX configuration saved to /tmp/juniper-srx-config.txt"
    print_status "Copy this configuration to your Juniper SRX device"
}

# Function to create monitoring and troubleshooting script
create_monitoring_script() {
    print_status "Creating monitoring script..."

    cat > /tmp/monitor-juniper-tunnel.sh << 'EOF'
#!/bin/bash

# Juniper SRX IPSec Tunnel Monitoring Script

echo "=== StrongSwan IPSec Status (External Server) ==="
swanctl --list-sas

echo -e "\n=== Connection Configuration ==="
swanctl --list-conns

echo -e "\n=== Security Associations ==="
ip xfrm state

echo -e "\n=== IPSec Policies ==="
ip xfrm policy

echo -e "\n=== Network Interfaces ==="
ip addr show

echo -e "\n=== Routing Table ==="
ip route show

echo -e "\n=== nftables Rules ==="
nft list ruleset | head -50

echo -e "\n=== Connection Statistics ==="
cat /proc/net/xfrm_stat

echo -e "\n=== IPSec Log Entries (last 20) ==="
journalctl -u strongswan -n 20 --no-pager

echo -e "\n=== Network Connectivity Test ==="
ping -c 3 8.8.8.8 2>/dev/null && echo "Internet connectivity: OK" || echo "Internet connectivity: FAILED"

echo -e "\n=== NAT Connection Tracking ==="
cat /proc/net/nf_conntrack | head -10
EOF

    chmod +x /tmp/monitor-juniper-tunnel.sh

    # Copy to external server
    scp -P "$EXTERNAL_SSH_PORT" /tmp/monitor-juniper-tunnel.sh "$EXTERNAL_USER@$EXTERNAL_SERVER":/usr/local/bin/
    ssh -p "$EXTERNAL_SSH_PORT" "$EXTERNAL_USER@$EXTERNAL_SERVER" "chmod +x /usr/local/bin/monitor-juniper-tunnel.sh"

    print_success "Monitoring script installed on external server"
}

# Function to display configuration summary
show_summary() {
    print_success "Juniper SRX IPSec tunnel configuration completed!"

    echo -e "\n${GREEN}Configuration Summary:${NC}"
    echo -e "• External Server: ${BLUE}${TUNNEL_EXTERNAL_IP}${NC} (StrongSwan Responder)"
    echo -e "• SRX Internal Network: ${BLUE}${INTERNAL_NETWORK}${NC}"
    echo -e "• External Network: ${BLUE}${EXTERNAL_NETWORK}${NC}"
    echo -e "• Pre-Shared Key: ${BLUE}$IPSEC_PSK${NC}"
    echo -e "• IKE Version: ${BLUE}$IKE_VERSION${NC}"

    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Configure the Juniper SRX using the configuration in /tmp/juniper-srx-config.txt"
    echo "2. SSH to SRX and apply the configuration commands"
    echo "3. Commit the configuration on the SRX"
    echo "4. The tunnel should establish automatically (SRX is initiator)"
    echo "5. Monitor tunnel: ssh -p 22123 root@195.95.177.8 /usr/local/bin/monitor-juniper-tunnel.sh"

    echo -e "\n${YELLOW}SRX Configuration File: ${BLUE}/tmp/juniper-srx-config.txt${NC}"
    echo -e "${YELLOW}External Server Monitoring: ${BLUE}ssh -p 22123 root@195.95.177.8 /usr/local/bin/monitor-juniper-tunnel.sh${NC}"

    echo -e "\n${YELLOW}Troubleshooting:${NC}"
    echo "• External server logs: ssh -p 22123 root@195.95.177.8 journalctl -u strongswan -f"
    echo "• SRX tunnel status: show security ike security-associations"
    echo "• SRX IPSec status: show security ipsec security-associations"
    echo "• Test connectivity: ping from SRX to ${TUNNEL_EXTERNAL_IP}"

    echo -e "\n${BLUE}Log file: $LOG_FILE${NC}"
}

# Main function
main() {
    print_status "Starting Juniper SRX IPSec tunnel configuration..."
    print_status "Log file: $LOG_FILE"

    echo -e "${BLUE}Configuration:${NC}"
    echo -e "• External Server: ${BLUE}$EXTERNAL_USER@$EXTERNAL_SERVER:$EXTERNAL_SSH_PORT${NC}"
    echo -e "• External Network: ${BLUE}$EXTERNAL_NETWORK${NC}"
    echo -e "• SRX Internal Network: ${BLUE}$INTERNAL_NETWORK${NC}"
    echo -e "• Generated PSK: ${BLUE}$IPSEC_PSK${NC}"
    echo

    # Test SSH connection
    if ! test_ssh_connection "$EXTERNAL_SERVER" "$EXTERNAL_SSH_PORT" "$EXTERNAL_USER"; then
        print_error "Cannot connect to external server. Please check SSH connectivity."
        exit 1
    fi

    # Configure external server
    configure_external_server
    
    # Create StrongSwan configuration
    create_strongswan_config
    
    # Configure nftables
    configure_nftables

    # Create Juniper SRX configuration
    create_juniper_config

    # Create monitoring tools
    create_monitoring_script

    # Show summary
    show_summary

    print_success "Configuration script completed!"
    print_warning "Please apply the Juniper SRX configuration manually using /tmp/juniper-srx-config.txt"
}

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Configure IPSec tunnel between external server and Juniper SRX"
    echo
    echo "Options:"
    echo "  --external-server IP    External server IP (default: 195.95.177.8)"
    echo "  --external-port PORT    External server SSH port (default: 22123)"
    echo "  --internal-network NET  SRX internal network (default: 192.168.100.0/24)"
    echo "  --external-network NET  External server network (default: 195.95.177.0/28)"
    echo "  --psk PSK               Pre-shared key (auto-generated if not specified)"
    echo "  --help                  Show this help"
    echo
    echo "Environment Variables:"
    echo "  IPSEC_PSK               Pre-shared key (alternative to --psk)"
    echo
    echo "Example:"
    echo "  $0"
    echo "  $0 --internal-network 10.0.1.0/24 --psk 'my-secret-key'"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --external-server)
            EXTERNAL_SERVER="$2"
            TUNNEL_EXTERNAL_IP="$2"
            shift 2
            ;;
        --external-port)
            EXTERNAL_SSH_PORT="$2"
            shift 2
            ;;
        --internal-network)
            INTERNAL_NETWORK="$2"
            shift 2
            ;;
        --external-network)
            EXTERNAL_NETWORK="$2"
            shift 2
            ;;
        --psk)
            IPSEC_PSK="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main "$@"