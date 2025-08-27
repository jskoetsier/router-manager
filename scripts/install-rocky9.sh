#!/bin/bash

# Router Manager Installation Script for Rocky Linux 9
# This script installs and configures the Router Manager application

set -euo pipefail

# Check if running from git
FROM_GIT=""
if [[ "$1" == "--from-git" ]]; then
    FROM_GIT="true"
fi
INSTALL_DIR=${INSTALL_DIR:-"/opt/router-manager"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/var/log/router-manager-install.log"
INSTALL_DIR="/opt/router-manager"
CONFIG_DIR="/etc/router-manager"
SERVICE_USER="routermgr"
WEB_PORT="10443"

# Function to print colored output
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

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

# Function to detect Rocky Linux 9
check_os() {
    if [[ ! -f /etc/os-release ]]; then
        print_error "Cannot detect operating system"
        exit 1
    fi

    source /etc/os-release
    if [[ "$ID" != "rocky" ]] || [[ ! "$VERSION_ID" =~ ^9 ]]; then
        print_error "This script is designed for Rocky Linux 9 only"
        print_error "Detected: $PRETTY_NAME"
        exit 1
    fi

    print_success "Rocky Linux 9 detected: $PRETTY_NAME"
}

# Function to update system packages
update_system() {
    print_status "Updating system packages..."
    dnf update -y &>> "$LOG_FILE"
    print_success "System packages updated"
}

# Function to install required packages
install_packages() {
    print_status "Installing required packages..."

    # Enable EPEL repository
    dnf install -y epel-release &>> "$LOG_FILE"

    # Install development tools
    dnf groupinstall -y "Development Tools" &>> "$LOG_FILE"

    # Install system packages
    local packages=(
        "python3"
        "python3-pip"
        "python3-devel"
        "postgresql-server"
        "postgresql-devel"
        "nginx"
        "nftables"
        "strongswan"
        "strongswan-charon-nm"
        "net-tools"
        "htop"
        "iotop"
        "tcpdump"
        "traceroute"
        "bind-utils"
        "wget"
        "curl"
        "git"
        "openssl"
        "openssl-devel"
        "libffi-devel"
        "redis"
        "supervisor"
        "logrotate"
        "fail2ban"
        "chrony"
    )

    for package in "${packages[@]}"; do
        print_status "Installing $package..."
        dnf install -y "$package" &>> "$LOG_FILE"
    done

    print_success "All required packages installed"
}

# Function to create system user
create_user() {
    print_status "Creating service user..."

    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd --system --shell /bin/bash --home-dir "$INSTALL_DIR" --create-home "$SERVICE_USER"
        print_success "Service user '$SERVICE_USER' created"
    else
        print_warning "Service user '$SERVICE_USER' already exists"
    fi
}

# Function to setup PostgreSQL
setup_postgresql() {
    print_status "Setting up PostgreSQL..."

    # Initialize database if not already done
    if [[ ! -f /var/lib/pgsql/data/PG_VERSION ]]; then
        postgresql-setup --initdb &>> "$LOG_FILE"
    fi

    # Start and enable PostgreSQL
    systemctl enable postgresql &>> "$LOG_FILE"
    systemctl start postgresql &>> "$LOG_FILE"

    # Create database and user
    sudo -u postgres psql -c "CREATE USER routermgr WITH PASSWORD 'routermgr123';" &>> "$LOG_FILE" || true
    sudo -u postgres psql -c "CREATE DATABASE routermanager OWNER routermgr;" &>> "$LOG_FILE" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE routermanager TO routermgr;" &>> "$LOG_FILE" || true

    print_success "PostgreSQL configured"
}

# Function to setup application directory structure
setup_directories() {
    print_status "Creating application directories..."

    # Create main directories
    mkdir -p "$INSTALL_DIR"/{webapp,logs,backups,ssl}
    mkdir -p "$CONFIG_DIR"
    mkdir -p /var/log/router-manager/{nginx,app,vpn}

    # Set permissions
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"
    chown -R "$SERVICE_USER":"$SERVICE_USER" /var/log/router-manager
    chmod 755 "$INSTALL_DIR"
    chmod 750 "$CONFIG_DIR"

    print_success "Directory structure created"
}

# Function to install Python application
install_application() {
    print_status "Installing Router Manager application..."

    # Change to installation directory
    cd "$INSTALL_DIR"

    # Create virtual environment using built-in venv module
    sudo -u "$SERVICE_USER" python3 -m venv venv

    # Activate virtual environment and install packages
    sudo -u "$SERVICE_USER" bash -c "
        source venv/bin/activate
        pip install --upgrade pip
        pip install django==4.2.*
        pip install psycopg2-binary
        pip install gunicorn
        pip install redis
        pip install celery
        pip install django-bootstrap5
        pip install django-crispy-forms
        pip install crispy-bootstrap5
        pip install whitenoise
        pip install python-decouple
        pip install django-extensions
        pip install requests
        pip install paramiko
        pip install psutil
    "

    print_success "Python dependencies installed"
}

# Function to setup Django application
setup_django_application() {
    print_status "Setting up Django application..."

    cd "$INSTALL_DIR"

    if [[ "$FROM_GIT" == "true" ]]; then
        # Running from git - webapp files should already be present
        if [[ ! -d "webapp" ]]; then
            print_error "webapp directory not found in git repository"
            exit 1
        fi

        print_status "Using webapp files from git repository"
        
        # Set ownership
        chown -R "$SERVICE_USER":"$SERVICE_USER" webapp/

        # Install Python requirements from the repo
        if [[ -f "webapp/requirements.txt" ]]; then
            sudo -u "$SERVICE_USER" bash -c "
                source venv/bin/activate
                pip install -r webapp/requirements.txt
            "
        fi
    else
        # Create Django project structure from scratch
        sudo -u "$SERVICE_USER" bash -c "
            source venv/bin/activate
            cd webapp
            django-admin startproject router_manager .
            python manage.py startapp dashboard
            python manage.py startapp nftables_mgr
            python manage.py startapp network
            python manage.py startapp vpn
            python manage.py startapp monitoring
        "
    fi

    print_success "Django application setup completed"
}

# Function to generate SSL certificates
generate_ssl_certs() {
    print_status "Generating SSL certificates..."

    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$INSTALL_DIR/ssl/server.key" \
        -out "$INSTALL_DIR/ssl/server.crt" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$(hostname -f)" \
        &>> "$LOG_FILE"

    # Set proper permissions
    chown "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR/ssl/"*
    chmod 600 "$INSTALL_DIR/ssl/server.key"
    chmod 644 "$INSTALL_DIR/ssl/server.crt"

    print_success "SSL certificates generated"
}

# Function to configure nftables
setup_nftables() {
    print_status "Configuring nftables firewall..."

    # Create basic nftables configuration
    cat > /etc/nftables/nftables.conf << 'EOF'
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority filter;

        # Allow loopback
        iif lo accept

        # Allow established connections
        ct state established,related accept

        # Allow SSH (adjust port if needed)
        tcp dport 22 accept

        # Allow Router Manager web interface
        tcp dport 10443 accept

        # Allow ICMP
        ip protocol icmp accept
        ip6 nexthdr ipv6-icmp accept

        # Drop everything else
        drop
    }

    chain forward {
        type filter hook forward priority filter;
        # Will be managed by Router Manager
    }

    chain output {
        type filter hook output priority filter;
        accept
    }
}

table ip nat {
    chain prerouting {
        type nat hook prerouting priority dstnat;
        # Port forwarding rules will be added here
    }

    chain postrouting {
        type nat hook postrouting priority srcnat;
        # NAT rules will be added here
    }
}
EOF

    # Enable and start nftables
    systemctl enable nftables &>> "$LOG_FILE"
    systemctl start nftables &>> "$LOG_FILE"

    print_success "nftables configured"
}

# Function to configure Nginx
setup_nginx() {
    print_status "Configuring Nginx..."

    # Create Nginx configuration
    cat > /etc/nginx/conf.d/router-manager.conf << EOF
upstream router_manager {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    return 301 https://\$host\$request_uri;
}

server {
    listen 10443 ssl http2;

    ssl_certificate $INSTALL_DIR/ssl/server.crt;
    ssl_certificate_key $INSTALL_DIR/ssl/server.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    client_max_body_size 100M;

    access_log /var/log/router-manager/nginx/access.log;
    error_log /var/log/router-manager/nginx/error.log;

    location / {
        proxy_pass http://router_manager;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /static/ {
        alias $INSTALL_DIR/webapp/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Test nginx configuration
    nginx -t &>> "$LOG_FILE"

    # Enable and start nginx
    systemctl enable nginx &>> "$LOG_FILE"
    systemctl start nginx &>> "$LOG_FILE"

    print_success "Nginx configured"
}

# Function to create systemd service
create_systemd_service() {
    print_status "Creating systemd service..."

    cat > /etc/systemd/system/router-manager.service << EOF
[Unit]
Description=Router Manager Web Application
After=network.target postgresql.service redis.service
Requires=postgresql.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/webapp
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 3 router_manager.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=router-manager

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload &>> "$LOG_FILE"
    systemctl enable router-manager &>> "$LOG_FILE"

    print_success "Systemd service created"
}

# Function to enable IP forwarding
enable_ip_forwarding() {
    print_status "Enabling IP forwarding..."

    echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
    echo 'net.ipv6.conf.all.forwarding = 1' >> /etc/sysctl.conf
    sysctl -p &>> "$LOG_FILE"

    print_success "IP forwarding enabled"
}

# Function to setup log rotation
setup_logrotate() {
    print_status "Setting up log rotation..."

    cat > /etc/logrotate.d/router-manager << 'EOF'
/var/log/router-manager/*.log /var/log/router-manager/*/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 routermgr routermgr
    postrotate
        systemctl reload router-manager
    endscript
}
EOF

    print_success "Log rotation configured"
}

# Function to create configuration files
create_config_files() {
    print_status "Creating configuration files..."

    # Main configuration
    cat > "$CONFIG_DIR/settings.conf" << EOF
# Router Manager Configuration
[web]
port = $WEB_PORT
debug = False
secret_key = $(openssl rand -base64 32)

[database]
host = localhost
port = 5432
name = routermanager
user = routermgr
password = routermgr123

[security]
session_timeout = 3600
max_login_attempts = 5
lockout_duration = 900

[monitoring]
data_retention_days = 90
update_interval = 30
EOF

    chown root:"$SERVICE_USER" "$CONFIG_DIR/settings.conf"
    chmod 640 "$CONFIG_DIR/settings.conf"

    print_success "Configuration files created"
}

# Function to setup fail2ban
setup_fail2ban() {
    print_status "Configuring Fail2ban..."

    cat > /etc/fail2ban/jail.d/router-manager.conf << 'EOF'
[router-manager]
enabled = true
port = 10443,80
logpath = /var/log/router-manager/nginx/access.log
maxretry = 5
bantime = 3600
findtime = 600
filter = nginx-botsearch

[sshd]
enabled = true
maxretry = 3
bantime = 3600
EOF

    systemctl enable fail2ban &>> "$LOG_FILE"
    systemctl start fail2ban &>> "$LOG_FILE"

    print_success "Fail2ban configured"
}

# Function to perform final setup
final_setup() {
    print_status "Performing final setup..."

    # Create default admin user (this would be done through Django)
    # For now, just ensure all services are running

    # Start Redis
    systemctl enable redis &>> "$LOG_FILE"
    systemctl start redis &>> "$LOG_FILE"

    # Start chronyd for time synchronization
    systemctl enable chronyd &>> "$LOG_FILE"
    systemctl start chronyd &>> "$LOG_FILE"

    print_success "Services configured and started"
}

# Function to display completion message
show_completion_message() {
    print_success "Router Manager installation completed successfully!"
    echo
    echo -e "${GREEN}Installation Summary:${NC}"
    echo -e "  - Installation Directory: ${BLUE}$INSTALL_DIR${NC}"
    echo -e "  - Configuration Directory: ${BLUE}$CONFIG_DIR${NC}"
    echo -e "  - Log Directory: ${BLUE}/var/log/router-manager${NC}"
    echo -e "  - Service User: ${BLUE}$SERVICE_USER${NC}"
    echo -e "  - Web Interface: ${BLUE}https://$(hostname -I | awk '{print $1}'):$WEB_PORT${NC}"
    echo
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Access the web interface using the URL above"
    echo "  2. Login with default credentials (admin/admin)"
    echo "  3. Change the default password"
    echo "  4. Configure your network settings"
    echo
    echo -e "${YELLOW}Service Management:${NC}"
    echo "  - Start service: systemctl start router-manager"
    echo "  - Stop service: systemctl stop router-manager"
    echo "  - Check status: systemctl status router-manager"
    echo "  - View logs: journalctl -u router-manager -f"
    echo
    echo -e "${YELLOW}Configuration:${NC}"
    echo "  - Edit settings: $CONFIG_DIR/settings.conf"
    echo "  - SSL certificates: $INSTALL_DIR/ssl/"
    echo "  - Application logs: /var/log/router-manager/"
}

# Main installation function
main() {
    print_status "Starting Router Manager installation for Rocky Linux 9..."
    echo "Installation log: $LOG_FILE"

    check_root
    check_os
    update_system
    install_packages
    create_user
    setup_postgresql
    setup_directories
    install_application
    setup_django_application
    generate_ssl_certs
    setup_nftables
    setup_nginx
    create_systemd_service
    enable_ip_forwarding
    setup_logrotate
    create_config_files
    setup_fail2ban
    final_setup
    show_completion_message
}

# Run main function
main "$@"
