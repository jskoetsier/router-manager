# Juniper SRX IPSec Tunnel Configuration

This directory contains scripts and documentation for configuring an IPSec tunnel between a remote server and a Juniper SRX running Junos version 12.1X46-D40.2, with full internet routing support.

## Configuration Overview

- **External Server**: 195.95.177.8 (StrongSwan Responder)
- **Juniper SRX**: Behind NAT, acts as initiator
- **Junos Version**: 12.1X46-D40.2
- **Tunnel Type**: Routed tunnel with full internet access
- **Authentication**: Pre-shared key (PSK)
- **IKE Version**: IKEv1 (better compatibility with older Junos)

## Network Architecture

```
Internet
   |
   | (NAT)
   |
[Juniper SRX] ----IPSec Tunnel----> [External Server 195.95.177.8]
   |                                        |
   | (192.168.100.0/24)                     | (195.95.177.0/28)
   |                                        |
[Internal Hosts] -------Internet Access-----> [Internet via NAT]
```

## Quick Start

### 1. Prerequisites

- SSH access to external server (195.95.177.8:22123) as root
- Administrative access to Juniper SRX
- Network connectivity from SRX to external server on ports 500 and 4500 (UDP)

### 2. Configure External Server

Run the setup script to configure the external server as StrongSwan responder:

```bash
cd scripts/
chmod +x setup-juniper-ipsec-responder.sh
./setup-juniper-ipsec-responder.sh
```

### 3. Configure Juniper SRX

The script will generate a configuration file `/tmp/juniper-srx-config.txt`. Apply it to your SRX:

```bash
# SSH to your Juniper SRX
ssh admin@your-srx-ip

# Enter configuration mode
configure

# Paste the configuration from juniper-srx-config.txt
# (The script output will show the exact commands)

# Commit the configuration
commit and-quit
```

### 4. Verify Tunnel Status

Monitor the tunnel establishment:

```bash
# On External Server
ssh -p 22123 root@195.95.177.8 /usr/local/bin/monitor-juniper-tunnel.sh

# On Juniper SRX
show security ike security-associations
show security ipsec security-associations
```

## Configuration Details

### External Server (StrongSwan)

The setup script configures:

- **StrongSwan**: IPSec daemon in responder mode
- **nftables**: Firewall rules for IPSec and NAT
- **Routing**: Internet access for SRX network
- **Monitoring**: Scripts for tunnel status

### Juniper SRX Configuration

Generated configuration includes:

- **IKE Proposal**: AES-256-CBC, SHA-1, DH Group 2
- **IPSec Proposal**: AES-256-CBC, HMAC-SHA1-96
- **Tunnel Interface**: st0.0 with appropriate MTU
- **Routing**: Default route through tunnel for internet access
- **Security Policies**: Allow traffic through tunnel
- **NAT**: Source NAT for internal hosts

### Network Parameters (Customizable)

```bash
# Default networks (can be changed via script parameters)
External Server Network: 195.95.177.0/28
SRX Internal Network: 192.168.100.0/24
Tunnel Interface: st0.0 (10.0.0.1/30)
```

## Script Usage

### Basic Usage

```bash
./setup-juniper-ipsec-responder.sh
```

### Advanced Usage

```bash
# Custom networks and PSK
./setup-juniper-ipsec-responder.sh \
  --internal-network 10.0.1.0/24 \
  --external-network 203.0.113.0/28 \
  --psk "your-secret-key"
```

### Available Options

- `--external-server IP`: External server IP (default: 195.95.177.8)
- `--external-port PORT`: SSH port (default: 22123)
- `--internal-network NET`: SRX network (default: 192.168.100.0/24)
- `--external-network NET`: External network (default: 195.95.177.0/28)
- `--psk PSK`: Pre-shared key (auto-generated if not specified)
- `--help`: Show help information

## Monitoring and Troubleshooting

### External Server Monitoring

```bash
# Real-time tunnel monitoring
ssh -p 22123 root@195.95.177.8 /usr/local/bin/monitor-juniper-tunnel.sh

# StrongSwan logs
ssh -p 22123 root@195.95.177.8 journalctl -u strongswan -f

# nftables status
ssh -p 22123 root@195.95.177.8 nft list ruleset

# Connection tracking
ssh -p 22123 root@195.95.177.8 cat /proc/net/nf_conntrack
```

### Juniper SRX Monitoring

```bash
# IKE status
show security ike security-associations
show security ike security-associations detail

# IPSec status
show security ipsec security-associations
show security ipsec security-associations detail

# Tunnel interface status
show interfaces st0.0
show interfaces st0.0 extensive

# Routing verification
show route

# Test connectivity
ping 195.95.177.8 source st0.0
ping 8.8.8.8 source st0.0

# Logs
show log messages | match IKE | last 20
show log messages | match IPSec | last 20
```

### Common Issues and Solutions

#### 1. Tunnel Not Establishing

**Symptoms**: No IKE or IPSec SAs shown
**Solutions**:
- Verify PSK matches on both sides
- Check UDP ports 500/4500 are open
- Ensure SRX can reach external server IP
- Verify external-interface setting on SRX

```bash
# On SRX - clear and retry
clear security ike security-associations
clear security ipsec security-associations

# Check reachability
ping 195.95.177.8 count 5
```

#### 2. Tunnel Established but No Traffic

**Symptoms**: SAs exist but ping/traffic fails
**Solutions**:
- Verify routing configuration
- Check security policies
- Confirm tunnel interface is up

```bash
# On SRX
show interfaces st0.0
show route 195.95.177.0/28
show security policies

# Test tunnel interface directly
ping 195.95.177.8 source st0.0
```

#### 3. Internet Access Not Working

**Symptoms**: Can reach external server but not internet
**Solutions**:
- Verify default route through tunnel
- Check NAT configuration on external server
- Ensure nftables rules allow forwarding

```bash
# On SRX
show route 0.0.0.0/0

# On External Server
ssh -p 22123 root@195.95.177.8 'nft list table inet juniper_nat'
```

#### 4. NAT Traversal Issues

**Symptoms**: Frequent disconnections or establishment failures
**Solutions**:
- Adjust NAT keepalive settings
- Increase DPD timeout values
- Check NAT device configuration

```bash
# On SRX - adjust keepalive (already configured in template)
set security ike gateway external-gw nat-keepalive 10
```

## Security Considerations

### Cryptographic Settings

- **IKE**: AES-256-CBC with SHA-1 (compatible with Junos 12.1X46-D40.2)
- **ESP**: AES-256-CBC with HMAC-SHA1-96
- **DH Group**: Group 2 (1024-bit MODP)
- **PFS**: Enabled for Phase 2

### Firewall Rules

- External server only accepts IPSec traffic and SSH
- SRX policies allow necessary tunnel traffic
- NAT rules properly configured for internet access

### Best Practices

1. **Change Default PSK**: Always use a strong, unique pre-shared key
2. **Monitor Logs**: Regularly check tunnel status and logs
3. **Update Firmware**: Keep Junos and StrongSwan updated when possible
4. **Network Segmentation**: Use appropriate security zones
5. **Access Control**: Limit administrative access to both devices

## Advanced Configuration

### Multiple Subnets

To route multiple subnets through the tunnel, modify the SRX configuration:

```bash
# Add additional static routes
set routing-options static route 10.0.0.0/8 next-hop st0.0
set routing-options static route 172.16.0.0/12 next-hop st0.0
```

### QoS and Traffic Shaping

```bash
# Example: Prioritize VoIP traffic
set class-of-service interfaces st0 unit 0 scheduler-map voip-map
```

### Redundancy

For high availability, consider:
- Multiple external servers with different PSKs
- Load balancing across tunnels
- Automatic failover configuration

## Compatibility Notes

### Junos Version 12.1X46-D40.2

- Supports IKEv1 and IKEv2 (IKEv1 recommended for stability)
- Limited to older cryptographic algorithms
- NAT-T support available
- Secure tunnel (st0) interfaces supported

### StrongSwan Compatibility

- Modern StrongSwan versions maintain backward compatibility
- Supports legacy algorithms needed for older Junos
- Excellent NAT traversal implementation
- Robust logging and debugging capabilities

## Files Created by Script

- `/tmp/juniper-srx-config.txt`: Complete SRX configuration
- `/tmp/juniper-ipsec-setup-YYYYMMDD-HHMMSS.log`: Setup log
- `/usr/local/bin/monitor-juniper-tunnel.sh`: Monitoring script (on external server)
- `/etc/swanctl/swanctl.conf`: StrongSwan configuration (on external server)
- `/etc/nftables/juniper-ipsec-nftables.nft`: Firewall rules (on external server)

## Performance Considerations

### Throughput

- Expect 50-200 Mbps throughput depending on:
  - CPU performance of both devices
  - Network latency and quality
  - Encryption overhead
  - MTU settings

### Optimization Tips

1. **MTU Tuning**: Configured to 1436 to avoid fragmentation
2. **CPU Usage**: Monitor both devices under load
3. **Connection Limits**: Consider concurrent connection limits
4. **Buffer Sizes**: Kernel network buffers may need tuning for high throughput

## Support and Maintenance

### Regular Maintenance Tasks

1. **Monitor Tunnel Health**: Use provided monitoring scripts
2. **Log Rotation**: Ensure logs don't fill disk space
3. **Certificate Renewal**: Not applicable for PSK-based setup
4. **Backup Configuration**: Regular backup of both device configurations

### Upgrading

When upgrading either device:
1. Test in lab environment first
2. Backup current working configuration
3. Plan for temporary tunnel downtime
4. Verify compatibility of new versions

For support or questions about this configuration, refer to:
- StrongSwan documentation: https://docs.strongswan.org/
- Juniper SRX documentation: https://www.juniper.net/documentation/
- This project's issue tracker for script-specific problems

---

**Note**: This configuration is optimized for Junos 12.1X46-D40.2. For newer Junos versions, consider upgrading to IKEv2 and stronger cryptographic algorithms for enhanced security.