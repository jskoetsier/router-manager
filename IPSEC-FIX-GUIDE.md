# IPsec Tunnel Internet Routing Fix Guide

## Problem Description

Your IPsec tunnel between two servers is established but the internal subnet `192.168.1.0/24` cannot access the internet through the tunnel. This guide provides the solution and explains how to fix the routing issue.

**Server Configuration:**
- **Internal Server:** `192.168.1.253` (SSH port 22, root access)
- **External Server:** `195.95.177.8` (SSH port 22123, root access)
- **Internal Network:** `192.168.1.0/24`
- **External Network:** `195.95.177.0/28`

## Root Cause Analysis

The issue is that while the IPsec tunnel is established, traffic from the internal network isn't being properly routed through the tunnel to reach the internet. Two main components are needed:

1. **DNAT on Internal Server:** Redirect internet-bound traffic to use the IPsec tunnel
2. **NAT on External Server:** Masquerade traffic from the tunnel to the internet

## Solution Overview

### How It Works

1. **Internal Server:** Uses DNAT to redirect internet traffic to `195.95.177.1`
2. **IPsec Tunnel:** Encrypts traffic destined for `195.95.177.0/28` network
3. **External Server:** NATs the decrypted traffic to the internet

## Quick Fix (Automated)

### Option 1: Fix Both Servers Remotely

If you're on your local machine and have SSH access to both servers:

```bash
cd /Users/johansebastiaan/dev/router-manager/scripts
./fix-ipsec-routing.sh --remote
```

This will:
- Connect to both servers via SSH
- Configure DNAT rules on the internal server
- Configure NAT rules on the external server
- Test the connectivity
- Create persistent configurations

### Option 2: Fix Servers Individually

**On Internal Server (192.168.1.253):**
```bash
# SSH to internal server
ssh root@192.168.1.253

# Download and run the fix script
wget https://raw.githubusercontent.com/.../fix-ipsec-routing.sh
chmod +x fix-ipsec-routing.sh
./fix-ipsec-routing.sh --internal
```

**On External Server (195.95.177.8):**
```bash
# SSH to external server
ssh -p 22123 root@195.95.177.8

# Download and run the fix script
wget https://raw.githubusercontent.com/.../fix-ipsec-routing.sh
chmod +x fix-ipsec-routing.sh
./fix-ipsec-routing.sh --external
```

## Manual Configuration (Step-by-Step)

### Internal Server Configuration

**1. Clean up previous configurations:**
```bash
nft delete table inet ipsec_internet 2>/dev/null || true
nft delete table inet internet_routing 2>/dev/null || true
nft delete table inet simple_forward 2>/dev/null || true
```

**2. Enable IP forwarding:**
```bash
sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-ipsec-routing.conf
```

**3. Create DNAT rules:**
```bash
# Create nftables table and chains
nft add table inet ipsec_routing
nft add chain inet ipsec_routing prerouting { type nat hook prerouting priority -100 \; }
nft add chain inet ipsec_routing forward { type filter hook forward priority 0 \; }

# DNAT internet traffic to force it through IPsec tunnel
nft add rule inet ipsec_routing prerouting ip saddr 192.168.1.0/24 ip daddr != 192.168.1.0/24 ip daddr != 195.95.177.0/28 dnat to 195.95.177.1

# Forward rules
nft add rule inet ipsec_routing forward ip saddr 192.168.1.0/24 accept
nft add rule inet ipsec_routing forward ct state established,related accept
```

### External Server Configuration

**1. Clean up previous configurations:**
```bash
nft delete table inet external_nat 2>/dev/null || true
nft delete table inet ipsec_nat 2>/dev/null || true
```

**2. Enable IP forwarding:**
```bash
sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-external-nat.conf
```

**3. Create NAT rules:**
```bash
# Get internet interface
INTERNET_INTERFACE=$(ip route | grep "^default" | awk '{print $5}' | head -1)

# Create nftables configuration
nft add table inet external_routing
nft add chain inet external_routing postrouting { type nat hook postrouting priority srcnat \; }
nft add chain inet external_routing forward { type filter hook forward priority filter \; }

# NAT rules
nft add rule inet external_routing postrouting ip saddr 192.168.1.253 oifname $INTERNET_INTERFACE masquerade
nft add rule inet external_routing postrouting ip saddr 192.168.1.0/24 oifname $INTERNET_INTERFACE masquerade

# Forward rules
nft add rule inet external_routing forward ip saddr 192.168.1.253 oifname $INTERNET_INTERFACE accept
nft add rule inet external_routing forward ip saddr 192.168.1.0/24 oifname $INTERNET_INTERFACE accept
nft add rule inet external_routing forward iifname $INTERNET_INTERFACE ct state established,related accept
```

## Testing the Solution

### From Internal Server

```bash
# Test internet connectivity
ping -c 3 8.8.8.8
ping -c 3 google.com

# Check IPsec tunnel statistics
swanctl --list-sas

# Verify nftables rules
nft list table inet ipsec_routing
```

### From External Server

```bash
# Test internet connectivity
ping -c 3 8.8.8.8

# Verify NAT rules
nft list table inet external_routing

# Check tunnel status
swanctl --list-sas
```

### From LAN Clients

From any machine in the `192.168.1.0/24` network:

```bash
# Test internet access (should now work through IPsec)
ping -c 3 8.8.8.8
curl -s ifconfig.me  # Should show external server's public IP
```

## Diagnostics

Use the diagnostic script to troubleshoot issues:

```bash
./diagnose-ipsec-routing.sh --full
```

This will check:
- IPsec tunnel status
- Current nftables rules
- IP forwarding status
- Internet connectivity
- Routing table

## Persistence

The automated script creates systemd services to ensure the configuration persists across reboots:

- **Internal Server:** `ipsec-routing.service`
- **External Server:** `external-nat.service`

### Manual Persistence

If you configured manually, create systemd services:

**Internal Server Service:**
```bash
cat > /etc/systemd/system/ipsec-routing.service << 'EOF'
[Unit]
Description=IPsec Internet Routing
After=network.target strongswan.service
Wants=strongswan.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/setup-ipsec-routing.sh

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ipsec-routing.service
systemctl start ipsec-routing.service
```

## Troubleshooting

### Common Issues

1. **IPsec tunnel not established:**
   ```bash
   # Check strongSwan logs
   journalctl -u strongswan -n 20

   # Restart strongSwan
   systemctl restart strongswan
   ```

2. **Internet access still not working:**
   ```bash
   # Verify DNAT rules are active
   nft list table inet ipsec_routing

   # Check tunnel statistics for traffic
   swanctl --list-sas | grep bytes
   ```

3. **NAT not working on external server:**
   ```bash
   # Verify masquerade rules
   nft list table inet external_routing

   # Check IP forwarding
   sysctl net.ipv4.ip_forward
   ```

### Debug Commands

```bash
# Check IPsec policies
ip xfrm policy

# Monitor traffic through tunnel
tcpdump -i any esp

# Test specific routes
ip route get 8.8.8.8

# Check nftables ruleset
nft list ruleset | grep -A5 -B5 "192.168.1"
```

## Key Files

- **Fix Script:** `/Users/johansebastiaan/dev/router-manager/scripts/fix-ipsec-routing.sh`
- **Diagnostic Script:** `/Users/johansebastiaan/dev/router-manager/scripts/diagnose-ipsec-routing.sh`
- **Alternative Solutions:**
  - `simple-working-solution.sh`
  - `working-internet-via-ipsec.sh`

## Summary

The solution uses DNAT on the internal server to redirect internet traffic through the IPsec tunnel, and NAT on the external server to masquerade the traffic to the internet. This allows the entire `192.168.1.0/24` subnet to access the internet through the encrypted IPsec tunnel.

After applying the fix, all devices in the `192.168.1.0/24` network will be able to reach the internet via the IPsec tunnel, and their traffic will appear to come from the external server's public IP address.
