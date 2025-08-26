# Changelog

All notable changes to Router Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-08-26

### Added
- **Core Infrastructure**
  - Django 4.2 web application framework
  - Bootstrap 5 responsive user interface
  - PostgreSQL database backend
  - Redis caching and session storage
  - Nginx reverse proxy with SSL/TLS support
  - Gunicorn WSGI application server

- **Authentication & Security**
  - User authentication and session management
  - Activity logging and audit trails
  - Role-based access control foundation
  - HTTPS-only web interface with self-signed certificates
  - CSRF protection and secure headers

- **Network Management**
  - Real-time network interface monitoring
  - IP forwarding configuration (IPv4/IPv6)
  - Basic NAT masquerading setup
  - Network interface status display
  - System network settings management

- **Firewall Management**
  - nftables integration and rule management
  - Port forwarding configuration interface
  - Basic firewall rule templates
  - Firewall status monitoring

- **VPN Management**
  - IPSec VPN tunnel configuration
  - StrongSwan integration
  - VPN tunnel creation and management forms
  - Pre-shared key generation
  - VPN connection status monitoring

- **System Monitoring**
  - Real-time CPU, memory, and disk usage display
  - Network interface statistics
  - System information dashboard
  - Service status monitoring
  - Performance metrics collection foundation

- **Installation & Deployment**
  - Automated installation scripts for Rocky Linux 9
  - Automated installation scripts for RHEL 9
  - Systemd service integration
  - Log rotation configuration
  - Fail2ban security hardening
  - SELinux policy configuration (RHEL)

- **User Interface**
  - Responsive Bootstrap 5 design
  - Multi-section navigation (Dashboard, Network, Firewall, VPN, Monitoring)
  - Real-time status updates with JavaScript
  - Form validation and error handling
  - Activity logging and system alerts interface

### Technical Implementation
- **Backend**: Django 4.2, PostgreSQL, Redis
- **Frontend**: Bootstrap 5, Chart.js, Font Awesome icons
- **System Integration**: nftables, StrongSwan, systemd
- **Security**: HTTPS, CSRF protection, audit logging
- **Deployment**: Automated scripts, service management

### Infrastructure
- Installation directory: `/opt/router-manager`
- Configuration directory: `/etc/router-manager`
- Log directory: `/var/log/router-manager`
- Service user: `routermgr`
- Web interface: HTTPS on port 443 (via nginx proxy)
- Application server: Gunicorn on localhost:8000

### Supported Platforms
- Red Hat Enterprise Linux (RHEL) 9
- Rocky Linux 9
- Architecture: x86_64, ARM64

### Default Credentials
- Username: `admin`
- Password: `admin` (must be changed on first login)

### Known Limitations
- Certificate management is placeholder (future implementation)
- Advanced firewall rules require manual configuration
- VPN user management is basic implementation
- Monitoring charts show limited historical data
- No backup/restore functionality yet
- Limited multi-user management

### Security Notes
- Default installation uses self-signed certificates
- Firewall rules should be carefully tested
- VPN configurations require proper network planning
- Regular security updates recommended

## [1.1.0] - 2025-08-26

### Added
- **🚀 Git-Based Deployment System**
  - Complete git repository integration for deployments
  - New `install-from-git.sh` script for automated git-based installations
  - Remote deployment script (`deploy-remote.sh`) for deploying to remote servers
  - Automatic repository cloning and updates during installation

- **📦 Enhanced Installation Scripts**
  - Fixed dependency issues with python3-virtualenv by using built-in venv module
  - Improved OS detection for Rocky Linux 9.x versions
  - Better error handling and logging during installation
  - Support for --from-git flag in installation scripts

- **🔄 Automatic Update System**
  - Remote update script (`router-manager-update`) created on target systems
  - Git-based update mechanism with automatic backup of local changes
  - Optional systemd timer for weekly automatic updates
  - Update verification and rollback capabilities

- **🌐 Remote Management Tools**
  - SSH-based deployment to remote hosts (tested on 192.168.1.253)
  - Remote OS compatibility checking
  - Automated service verification and health checks
  - Comprehensive deployment status reporting

- **🔧 Installation Improvements**
  - Better virtual environment handling using python3 -m venv
  - Enhanced package dependency resolution
  - Improved SSL certificate generation and management
  - More robust PostgreSQL setup and user creation

### Fixed
- Rocky Linux 9.6 compatibility issues in deployment scripts
- Python virtual environment dependency conflicts
- OS detection regex patterns for various Rocky Linux versions
- Service startup and configuration verification

### Technical Implementation
- **Repository URL**: `https://github.com/jskoetsier/router-manager.git`
- **Deployment Method**: Git clone + automated installation
- **Update Mechanism**: Git pull with service restart
- **Remote Access**: SSH-based deployment and management

## [Unreleased]

### Planned Features
- Advanced monitoring dashboards
- Enhanced VPN certificate management
- Backup and restore functionality
- Multi-user role management
- Advanced firewall rule templates
- Network traffic analysis
- Automated security updates
- Cloud provider integration
- Docker container deployment option
- Ansible playbook integration

---

**Note**: This is the initial release of Router Manager. Future versions will expand functionality based on user feedback and requirements.
