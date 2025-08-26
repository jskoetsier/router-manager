# Router Manager

**Version 1.0.0** - A comprehensive web-based router management system for RHEL 9 and Rocky Linux 9 distributions. This application provides an intuitive web interface for managing network configurations, firewall rules, VPN tunnels, and system monitoring.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Django 4.2](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)

## 🚀 Features

### ✅ Current Features (v1.0.0)
- **🖥️ Modern Web Interface**: Responsive Django-based UI with Bootstrap 5 styling
- **🛡️ Firewall Management**: Complete nftables integration with port forwarding and rule management
- **🌐 Network Configuration**: Advanced IP forwarding, NAT, and network interface management
- **🔐 IPSec VPN Tunnels**: Full StrongSwan integration for site-to-site and client VPN
- **📊 System Monitoring**: Real-time CPU, memory, disk usage with dashboard graphs
- **👤 User Management**: Secure authentication with activity logging and audit trails
- **🔧 Automated Installation**: One-command installation for RHEL 9 and Rocky Linux 9
- **🔒 Security Hardening**: HTTPS-only, fail2ban integration, and comprehensive logging

### 🎯 Supported Use Cases
- **Home Lab Router**: Convert Linux server into feature-rich router
- **Small Business Gateway**: Secure internet gateway with VPN capabilities
- **Network Testing**: Isolated network environments for development
- **Educational Platform**: Learn networking concepts with hands-on interface
- **Branch Office Connectivity**: Site-to-site VPN connections

### 🖥️ Supported Distributions
- **Red Hat Enterprise Linux (RHEL) 9** - Full support with subscription management
- **Rocky Linux 9** - Complete feature parity with RHEL
- **Architecture**: x86_64, ARM64 (aarch64)

## 🏗️ Architecture

```
router-manager/
├── 📁 webapp/                    # Django web application
│   ├── 📁 router_manager/       # Main Django project settings
│   ├── 📁 dashboard/            # System dashboard and monitoring
│   ├── 📁 nftables_mgr/         # Firewall and nftables management
│   ├── 📁 network/              # Network interface configuration
│   ├── 📁 vpn/                  # IPSec VPN tunnel management
│   ├── 📁 monitoring/           # Advanced system monitoring
│   ├── 📁 templates/            # HTML templates
│   └── 📁 static/               # CSS, JavaScript, images
├── 📁 scripts/                  # Installation and management scripts
├── 📄 CHANGELOG.md             # Version history and changes
├── 📄 ROADMAP.md               # Future development plans
└── 📄 README.md                # This file
```

## ⚡ Quick Start

### 🔧 Prerequisites
- **Operating System**: RHEL 9 or Rocky Linux 9
- **Privileges**: Root or sudo access
- **Network**: Internet connection for package installation
- **Hardware**: Minimum 2GB RAM, 10GB disk space

### 🚀 One-Command Installation

#### Rocky Linux 9:
```bash
curl -fsSL https://raw.githubusercontent.com/your-org/router-manager/main/scripts/install-rocky9.sh | sudo bash
```

#### RHEL 9:
```bash
curl -fsSL https://raw.githubusercontent.com/your-org/router-manager/main/scripts/install-rhel9.sh | sudo bash
```

### 📥 Manual Installation

1. **Clone the repository**:
```bash
git clone https://github.com/your-org/router-manager.git
cd router-manager
```

2. **Run installation script**:
```bash
# For Rocky Linux 9
sudo ./scripts/install-rocky9.sh

# For RHEL 9  
sudo ./scripts/install-rhel9.sh
```

3. **Access the web interface**:
```
https://your-server-ip
```

### 🔑 Default Credentials
- **Username**: `admin`
- **Password**: `admin`
- **⚠️ Important**: Change password on first login

## 📖 Usage Guide

### 🖥️ Web Interface Access
1. Open your browser and navigate to `https://your-server-ip`
2. Accept the self-signed certificate warning
3. Login with default credentials
4. Follow the setup wizard to configure your router

### 🌐 Network Configuration
- **IP Forwarding**: Enable/disable IPv4 and IPv6 forwarding
- **NAT Configuration**: Set up masquerading for internet sharing  
- **Interface Management**: Configure network interfaces and IP addresses
- **Routing**: Manage static routes and routing policies

### 🛡️ Firewall Management
- **Basic Rules**: Allow/deny traffic by port, protocol, or IP
- **Port Forwarding**: Redirect external traffic to internal services
- **Templates**: Pre-configured rule sets for common scenarios
- **Real-time Status**: Monitor active connections and blocked traffic

### 🔐 VPN Configuration
- **Site-to-Site**: Connect multiple networks securely
- **Road Warrior**: Remote user access via VPN clients
- **Certificate Management**: Generate and manage SSL certificates
- **Connection Monitoring**: Real-time VPN tunnel status

### 📊 System Monitoring
- **Resource Usage**: CPU, memory, disk, and network utilization
- **Performance Graphs**: Historical data with Chart.js visualization
- **Service Status**: Monitor critical system services
- **Alerting**: Configurable alerts for system events

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