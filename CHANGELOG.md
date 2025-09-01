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

## [1.4.0] - 2025-09-01

### Added
- **🌍 Complete Nginx Reverse Proxy Management**
  - Full nginx configuration management through intuitive web interface
  - Create, edit, view, and delete nginx proxy configurations
  - Real-time nginx configuration generation and deployment
  - Integration with system nginx service for live configuration updates
  - Support for HTTP and HTTPS upstream servers with custom headers

- **🔒 Automated SSL Certificate Management**  
  - Integrated Let's Encrypt certificate automation via certbot
  - One-click SSL certificate generation for configured domains
  - Automatic certificate renewal setup with cron scheduling
  - Certificate status monitoring and expiry date tracking
  - Support for webroot-based domain validation (ACME challenge)

- **📋 Advanced Domain Configuration**
  - Comprehensive domain validation with regex patterns
  - Upstream server configuration with host, port, and protocol selection
  - Custom proxy timeout settings (connect, read, send timeouts)
  - Rate limiting configuration with requests per minute controls
  - Access and error logging configuration per domain

- **🚀 One-Click Deployment System**
  - Deploy nginx configurations with automatic service reload
  - Real-time deployment status feedback and error handling
  - Configuration validation before deployment to prevent service disruption
  - Rollback capabilities for failed deployments
  - Integration with SSL certificate generation workflow

- **📊 Enhanced Monitoring & Status**
  - Real-time nginx service status monitoring
  - Configuration validation and syntax checking
  - Nginx version detection and display
  - Deployment history and audit logging
  - SSL certificate status and expiry monitoring

- **🗑️ Complete CRUD Operations**
  - Delete functionality with safety confirmation dialogs
  - Edit configurations with live validation
  - Duplicate configuration creation for quick setup
  - Bulk operations support for multiple configurations
  - Configuration export and import capabilities

- **🎨 Enhanced User Interface**
  - Added nginx navigation to main navbar and dashboard
  - Professional nginx management interface with status indicators
  - Responsive design optimized for mobile and desktop
  - Real-time status updates with color-coded badges
  - Comprehensive configuration details view with action buttons

- **🔧 System Integration Improvements**
  - Enhanced sudo permissions handling for nginx operations
  - Automatic nginx directory creation and management
  - Improved error handling with detailed user feedback
  - Better integration with existing router management workflow
  - Support for both bare metal and containerized deployments

### Enhanced
- **🏠 Dashboard Integration**
  - Added nginx quick action button to main dashboard
  - Nginx status widget with service health indicators
  - Quick access to nginx configurations and deployment status
  - Integration with existing monitoring and system status displays

- **📱 Mobile Responsiveness**
  - Optimized nginx management interface for mobile devices
  - Touch-friendly action buttons and navigation
  - Responsive table layouts for configuration lists
  - Mobile-optimized forms and validation feedback

- **🔒 Security Enhancements**
  - Enhanced validation for domain names and network addresses
  - Improved command execution with proper privilege escalation
  - Better error handling to prevent information disclosure
  - SSL-first approach with automatic HTTPS redirects

### Fixed
- **🐛 Database Data Consistency**
  - Fixed incorrect domain name display (git.koetsier.org vs gitlab.koetsier.org)
  - Corrected deployment status indicators to reflect actual SSL certificate status
  - Updated nginx configuration records to match production deployments
  - Fixed domain validation and display inconsistencies

- **🎨 User Interface Improvements**
  - Added favicon support for better branding and user experience
  - Fixed base template DOCTYPE typo causing potential rendering issues
  - Improved navigation consistency across all nginx management pages
  - Enhanced visual feedback for configuration actions and status

- **⚙️ Production Deployment Issues**
  - Resolved nginx configuration conflicts during SSL certificate generation
  - Fixed certbot integration with proper webroot configuration
  - Improved nginx service management with better error handling
  - Enhanced certificate directory creation and permission management

### Technical Implementation
- **Backend Architecture**
  - Created comprehensive nginx management system in `nginx_mgr` Django app
  - Implemented `NginxManager` class for service integration and configuration management
  - Added `CertbotManager` class for SSL certificate lifecycle management
  - Created deployment logging system for audit trails and troubleshooting

- **Database Models**
  - `NginxProxyConfig` model for storing nginx configurations
  - `SSLCertificate` model for tracking certificate status and metadata
  - `NginxDeploymentLog` model for deployment history and audit trails
  - Comprehensive model relationships and validation rules

- **Frontend Implementation**
  - Django ModelForms with Bootstrap 5 styling and real-time validation
  - Responsive templates with status indicators and action buttons
  - JavaScript integration for real-time status updates and user feedback
  - Mobile-optimized interface design with touch-friendly controls

### Production Success
- Successfully deployed nginx reverse proxy management to production servers
- SSL certificate generation verified working with Let's Encrypt
- All nginx management functionality tested and verified on remote servers
- Production deployment includes git.koetsier.org with valid SSL certificate

## [1.3.0] - 2025-08-27

### Added
- **🛣️ Static Routes Management System**
  - Complete CRUD operations for static routes through web interface
  - Form-based route creation with validation for CIDR notation and IP addresses
  - Real-time application of routes to system routing table
  - Persistent route configuration across system reboots
  - Integration with network interface selection and metric configuration
  - Side-by-side comparison of configured routes vs. live system routing table

- **🔧 Enhanced VPN Statistics & Monitoring**
  - Improved VPN tunnel statistics parsing for internal servers
  - Enhanced error handling when `swanctl` command is missing or unavailable
  - Better service validation with graceful degradation when StrongSwan is not running
  - Automatic detection of `swanctl` command location across different installations
  - Timeout protection for VPN commands that might hang
  - More informative error messages instead of generic failures

- **🌐 Network Management Enhancements**
  - Added static routes section to network management navigation
  - New RouteForm with comprehensive validation for destinations, gateways, and interfaces
  - Help examples and documentation within the route creation interface
  - Route status indicators and metrics display
  - Integration with existing network interface management

### Enhanced
- **🎨 User Interface Improvements**
  - New static routes list page with sortable tables and status indicators
  - Enhanced route creation form with contextual help and validation
  - Improved network homepage with static routes quick access
  - Better responsive design for route management on mobile devices
  - Color-coded route status badges and interface indicators

- **🔒 Security & Configuration**
  - Fixed CSRF trusted origins to include external server domain (195.95.177.8:10443)
  - Enhanced system integration with proper sudo permissions for route commands
  - Improved error handling and logging for route operations
  - Better validation for network addresses and CIDR notation

### Fixed
- **🐛 Server Deployment Issues**
  - Resolved missing `django-widget-tweaks` dependency on external server
  - Fixed Redis service startup and configuration on external server
  - Corrected CSRF verification failures for external domain access
  - Improved service restart handling and process management

- **⚙️ VPN Statistics Reliability**
  - Fixed VPN statistics retrieval on servers without proper StrongSwan setup
  - Enhanced output parsing for different `swanctl` command formats
  - Better error handling when VPN services are not available
  - Improved timeout handling for hung VPN status commands

### Technical Implementation
- **Backend Architecture**
  - Created `network.utils.add_static_route()` for system route application
  - Added `network.utils.make_route_persistent()` for boot persistence
  - Implemented `network.utils.delete_static_route()` for route removal
  - Enhanced VPN utils with better service detection and error handling
  - Database integration with existing Route model for persistence

- **Frontend Implementation**
  - New RouteForm with Django ModelForm validation
  - Static routes list and management templates
  - Enhanced network navigation with static routes integration
  - Improved form validation and user feedback systems

### Deployment Success
- Successfully deployed to both internal server (192.168.1.253) and external server (195.95.177.8)
- All static route functionality verified working in production
- VPN statistics now work reliably across different server configurations
- Redis service properly configured and running on both servers

## [1.2.0] - 2025-08-27

### Added
- **🔥 Complete nftables Firewall Management**
  - Full web-based firewall rule creation and management interface
  - Real-time rule application to live nftables configuration
  - Comprehensive form validation for IP addresses, ports, and CIDR notation
  - Database persistence for rule management and audit trails
  - Support for TCP, UDP, ICMP, and all protocols with flexible filtering

- **🚀 Advanced Port Forwarding (DNAT)**
  - Complete DNAT rule configuration through web interface
  - External to internal port mapping with protocol selection
  - Automatic forward chain rule creation for allowed traffic
  - Port conflict detection and validation
  - Live application of port forwarding rules to nftables

- **📊 Enhanced Rule Visualization**
  - Clean, organized display of firewall rules in structured tables
  - Separate views for database-saved rules and active system rules
  - Protocol and action color-coded badges for quick identification
  - Rule priority ordering and status indicators
  - Collapsible raw nftables configuration view for advanced users

- **🛠️ Advanced Form System**
  - Django ModelForms with comprehensive validation
  - IP address and CIDR notation validation
  - Port range validation (1-65535)
  - Protocol-specific field validation (ports only for TCP/UDP)
  - User-friendly error messages and form field help text

- **⚡ Live System Integration**
  - Rules applied immediately to nftables upon creation
  - Automatic table and chain creation (filter, nat, input, forward, prerouting)
  - Comment-based rule identification for management
  - Error handling and rollback on failed rule application
  - Success/failure feedback to users through Django messages

### Enhanced
- **🎨 User Interface Improvements**
  - Fixed Django template syntax errors preventing page loads
  - Improved responsive design for rule management pages
  - Better form layouts with examples and validation feedback
  - Enhanced status displays with proper badge styling
  - Professional rule listing with sortable tables

- **🔒 Security and Validation**
  - Added CSRF trusted origins for HTTPS access
  - Fixed Django package dependencies and imports
  - Comprehensive input validation and sanitization
  - Secure command execution with proper sudo privileges
  - Protection against common web security vulnerabilities

### Fixed
- **🐛 Critical Template Issues**
  - Resolved Django `TemplateSyntaxError` from complex conditional expressions
  - Fixed `bootstrap5` vs `django_bootstrap5` app name configuration
  - Corrected package dependencies in requirements.txt
  - Fixed CSRF verification failures on form submissions
  - Eliminated template parsing errors across all nftables pages

- **⚙️ Deployment and Configuration**
  - Fixed package installation conflicts on remote server
  - Resolved Django import errors and virtual environment issues
  - Corrected service startup failures due to missing dependencies
  - Fixed URL routing and view function imports

### Technical Implementation
- **Backend Architecture**
  - Created `network.utils.create_nftables_rule()` for live rule application
  - Added `network.utils.create_port_forward_rule()` for DNAT management
  - Implemented `network.utils.parse_nftables_rules()` for rule parsing
  - Enhanced views with proper POST request handling and form processing
  - Database models for rule persistence with user tracking and timestamps

- **Frontend Implementation**
  - Django ModelForms with Bootstrap 5 styling and validation
  - Responsive templates with proper error handling and user feedback
  - Dynamic form fields with contextual help and examples
  - Status indicators and progress feedback for rule operations

### Deployment Success
- Successfully tested and deployed to remote server (192.168.1.253:10443)
- All nftables functionality verified working in production environment
- Forms successfully create and apply rules to live system
- Web interface fully accessible without errors

## [1.1.3] - 2025-08-27

### Fixed
- **🌐 Network Interface Display Issues**
  - Fixed network interface detection and display on network homepage
  - Added proper sudo permissions for ip commands in Django context
  - Fixed container-style interface name parsing (e.g., `eth0@if35`)
  - Network interfaces now correctly display with IP addresses and status

- **📋 Routing Table Template Errors**
  - Completely redesigned routing table template to eliminate Django template syntax errors
  - Removed invalid `{% break %}` statements that caused `TemplateSyntaxError`
  - Added Python-based route parsing function for structured data display
  - Enhanced route display with proper destination, gateway, interface, protocol, and metric columns
  - Added separate IPv4 and IPv6 route sections with clean table formatting

- **🛡️ Firewall Rules Display**
  - Fixed nftables rules display functionality
  - Improved error handling for missing NAT tables
  - Enhanced rules list template with proper rule count and status display
  - Added better error messaging when nftables commands fail

- **⚙️ Network System Settings**
  - Fixed IP forwarding status display and toggle functionality
  - Improved NAT configuration interface with interface selection
  - Added IPv6 forwarding support alongside IPv4
  - Enhanced system settings template with better status indicators

- **🎨 Template Syntax and UI Improvements**
  - Fixed Django template syntax errors across network management pages
  - Simplified template logic to avoid complex parsing in templates
  - Improved responsive design for network status displays
  - Added proper badge styling for status indicators

### Technical Improvements
- **Backend Enhancements**
  - Added `parse_route_line()` function for structured route data processing
  - Improved error handling in network utility functions
  - Enhanced command execution with proper sudo privileges for system commands
  - Better container environment compatibility for network interface detection

- **Frontend Enhancements**
  - Cleaner table displays for network information
  - Improved status badges and indicators
  - Better responsive design for network management sections
  - Enhanced user experience with proper loading states and error messages

### Deployment
- All fixes have been tested and deployed to remote server infrastructure
- Network management pages are now fully functional without template errors
- System status displays work correctly in production environments

## [1.1.2] - 2025-08-26

### Fixed
- **🔧 Database Schema Migration Issue**
  - Fixed `ProgrammingError: column vpn_vpntunnel.local_id does not exist`
  - Resolved database schema mismatch between model fields and actual table columns
  - Successfully migrated from `local_ip`/`remote_ip` to `local_id`/`remote_id` column names
  - Reset and re-applied VPN app migrations to ensure database consistency

- **⚙️ Service Stability Improvements**
  - Fixed Django bootstrap5 configuration conflicts preventing service startup
  - Ensured proper virtual environment and dependency management
  - Verified Router Manager service runs successfully with all worker processes
  - Confirmed all web interfaces respond correctly (login, dashboard, VPN pages)

### Technical Details
- Used `python manage.py migrate vpn zero` to reset migrations cleanly
- Re-applied migrations with correct field names for flexible identity support
- Verified database connectivity and model operations work properly
- All HTTP endpoints now return expected status codes (200 for login, 302 for authenticated pages)

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
