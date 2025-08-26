# Router Manager

A comprehensive web-based router management system for RHEL 9 and Rocky Linux 9 distributions. This application provides an intuitive web interface for managing network configurations, firewall rules, VPN tunnels, and system monitoring.

## Features

### Current Features
- **Web Interface**: Modern Django-based UI with Bootstrap styling
- **nftables Management**: Configure port forwarding and firewall rules
- **System Network Settings**: Manage IP forwarding, NAT, and routing
- **IPSec VPN Tunnels**: Create and manage VPN configurations
- **Resource Monitoring**: Real-time graphs of system resource usage
- **Auto-Updates**: Automatic system and software updates

### Supported Distributions
- Red Hat Enterprise Linux (RHEL) 9
- Rocky Linux 9

## Architecture

```
router-manager/
├── webapp/                 # Django web application
│   ├── router_manager/    # Main Django project
│   ├── dashboard/         # Dashboard app
│   ├── nftables/         # nftables management
│   ├── network/          # Network configuration
│   ├── vpn/              # IPSec VPN management
│   ├── monitoring/       # System monitoring
│   └── static/           # Static files (CSS, JS, images)
├── scripts/              # Installation and management scripts
├── config/               # Configuration files
├── systemd/              # Systemd service files
└── docs/                 # Documentation
```

## Installation

### Prerequisites
- RHEL 9 or Rocky Linux 9
- Root or sudo privileges
- Internet connection for package installation

### Quick Install

#### For Rocky Linux 9:
```bash
curl -fsSL https://raw.githubusercontent.com/your-repo/router-manager/main/scripts/install-rocky9.sh | sudo bash
```

#### For RHEL 9:
```bash
curl -fsSL https://raw.githubusercontent.com/your-repo/router-manager/main/scripts/install-rhel9.sh | sudo bash
```

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/router-manager.git
cd router-manager
```

2. Run the appropriate installation script:
```bash
# For Rocky Linux 9
sudo ./scripts/install-rocky9.sh

# For RHEL 9
sudo ./scripts/install-rhel9.sh
```

3. Access the web interface:
```
https://your-server-ip:8443
```

Default credentials:
- Username: `admin`
- Password: `admin` (change on first login)

## Configuration

### Network Interface
The application listens on all interfaces by default on port 8443 (HTTPS). You can modify this in:
```bash
/etc/router-manager/settings.conf
```

### Firewall Configuration
The installer automatically configures nftables rules to allow web access. Manual configuration can be done through the web interface.

### SSL Certificates
Self-signed certificates are generated during installation. For production use, replace with proper certificates:
```bash
/etc/router-manager/ssl/
```

## Usage

### Dashboard
- Overview of system status and network interfaces
- Quick access to common tasks
- Real-time monitoring widgets

### nftables Management
- Create and manage firewall rules
- Configure port forwarding
- NAT configuration
- Rule templates for common scenarios

### Network Settings
- Enable/disable IP forwarding
- Configure routing tables
- Manage network interfaces
- DHCP settings

### VPN Management
- IPSec tunnel configuration
- Certificate management
- Connection monitoring
- Automated setup wizards

### Monitoring
- CPU, Memory, and Disk usage graphs
- Network traffic monitoring
- Active connections display
- Historical data retention

## Security

### Authentication
- Web-based authentication with session management
- Password complexity requirements
- Session timeout configuration
- Failed login attempt protection

### Network Security
- HTTPS-only web interface
- Strong SSL/TLS configuration
- IP-based access restrictions
- Audit logging

### System Security
- Minimal privilege principle
- Service isolation
- Secure configuration defaults
- Regular security updates

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status router-manager

# Check logs
sudo journalctl -u router-manager -f
```

#### Web Interface Inaccessible
```bash
# Check firewall rules
sudo nft list ruleset

# Verify port binding
sudo netstat -tlnp | grep 8443
```

#### VPN Connection Issues
```bash
# Check IPSec status
sudo systemctl status strongswan

# View VPN logs
sudo tail -f /var/log/router-manager/vpn.log
```

### Log Files
- Application logs: `/var/log/router-manager/`
- Web server logs: `/var/log/router-manager/nginx/`
- System logs: `/var/log/messages`

## Development

### Setting up Development Environment

1. Install development dependencies:
```bash
sudo dnf install python3-devel postgresql-devel gcc
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Run development server:
```bash
cd webapp
python manage.py runserver 0.0.0.0:8000
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: [docs/](docs/)
- Issues: GitHub Issues
- Community: [Discussions](https://github.com/your-repo/router-manager/discussions)

## Acknowledgments

- Django framework
- Bootstrap UI framework
- nftables project
- strongSwan IPSec implementation
- Chart.js for monitoring graphs