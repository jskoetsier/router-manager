#!/bin/bash

# Router Manager Git-based Installation Script
# This script clones the repository and installs Router Manager from git

set -euo pipefail

# Configuration
REPO_URL="https://github.com/jskoetsier/router-manager.git"
INSTALL_DIR="/opt/router-manager"
CONFIG_DIR="/etc/router-manager"
SERVICE_USER="routermgr"
BRANCH="main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/var/log/router-manager-install.log"

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

# Function to detect OS
detect_os() {
    if [[ ! -f /etc/os-release ]]; then
        print_error "Cannot detect operating system"
        exit 1
    fi

    source /etc/os-release

    if [[ "$ID" == "rocky" && "$VERSION_ID" =~ ^9 ]]; then
        OS_TYPE="rocky9"
        print_success "Rocky Linux 9 detected: $PRETTY_NAME"
    elif [[ "$ID" == "rhel" && "$VERSION_ID" =~ ^9 ]]; then
        OS_TYPE="rhel9"
        print_success "RHEL 9 detected: $PRETTY_NAME"
    else
        print_error "Unsupported operating system: $PRETTY_NAME"
        print_error "This script supports Rocky Linux 9 and RHEL 9 only"
        exit 1
    fi
}

# Function to install git if not present
install_git() {
    if ! command -v git &> /dev/null; then
        print_status "Installing git..."
        dnf install -y git &>> "$LOG_FILE"
        print_success "Git installed"
    else
        print_success "Git is already installed"
    fi
}

# Function to clone or update repository
setup_repository() {
    print_status "Setting up Router Manager repository..."

    if [[ -d "$INSTALL_DIR/.git" ]]; then
        print_status "Repository exists, updating..."
        cd "$INSTALL_DIR"

        # Backup any local changes
        if [[ -n "$(git status --porcelain)" ]]; then
            print_warning "Local changes detected, creating backup..."
            git stash push -m "Auto-backup before update $(date)" &>> "$LOG_FILE"
        fi

        # Update repository
        git fetch origin &>> "$LOG_FILE"
        git checkout "$BRANCH" &>> "$LOG_FILE"
        git pull origin "$BRANCH" &>> "$LOG_FILE"

        print_success "Repository updated to latest version"
    else
        print_status "Cloning repository..."

        # Remove existing directory if it exists but is not a git repo
        if [[ -d "$INSTALL_DIR" ]]; then
            print_warning "Removing existing non-git directory"
            rm -rf "$INSTALL_DIR"
        fi

        # Clone repository
        git clone "$REPO_URL" "$INSTALL_DIR" &>> "$LOG_FILE"
        cd "$INSTALL_DIR"
        git checkout "$BRANCH" &>> "$LOG_FILE"

        print_success "Repository cloned successfully"
    fi

    # Show current version
    if [[ -f "$INSTALL_DIR/VERSION" ]]; then
        VERSION=$(cat "$INSTALL_DIR/VERSION")
        print_success "Router Manager version: $VERSION"
    fi
}

# Function to run the appropriate installation script
run_installation() {
    print_status "Running installation for $OS_TYPE..."

    cd "$INSTALL_DIR"

    case "$OS_TYPE" in
        "rocky9")
            if [[ -f "scripts/install-rocky9.sh" ]]; then
                chmod +x scripts/install-rocky9.sh
                ./scripts/install-rocky9.sh --from-git
            else
                print_error "Rocky Linux 9 installation script not found"
                exit 1
            fi
            ;;
        "rhel9")
            # First try the no-subscription version
            if [[ -f "scripts/install-rhel9-no-subscription.sh" ]]; then
                print_status "Using RHEL 9 installation script (no subscription required)"
                chmod +x scripts/install-rhel9-no-subscription.sh
                ./scripts/install-rhel9-no-subscription.sh --from-git
            elif [[ -f "scripts/install-rhel9.sh" ]]; then
                print_warning "Using standard RHEL 9 installation script (subscription required)"
                chmod +x scripts/install-rhel9.sh
                ./scripts/install-rhel9.sh --from-git
            else
                print_error "RHEL 9 installation script not found"
                exit 1
            fi
            ;;
        *)
            print_error "Unsupported OS type: $OS_TYPE"
            exit 1
            ;;
    esac
}

# Function to create update script
create_update_script() {
    print_status "Creating update script..."

    cat > /usr/local/bin/router-manager-update << 'EOF'
#!/bin/bash
# Router Manager Update Script

set -euo pipefail

INSTALL_DIR="/opt/router-manager"
LOG_FILE="/var/log/router-manager-update.log"

echo "$(date): Starting Router Manager update..." >> "$LOG_FILE"

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    echo "ERROR: Router Manager installation directory is not a git repository" >> "$LOG_FILE"
    exit 1
fi

cd "$INSTALL_DIR"

# Check for updates
echo "Checking for updates..." >> "$LOG_FILE"
git fetch origin >> "$LOG_FILE" 2>&1

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u})

if [[ "$LOCAL" == "$REMOTE" ]]; then
    echo "Router Manager is already up to date." >> "$LOG_FILE"
    echo "Router Manager is already up to date."
    exit 0
fi

echo "Updates available, updating Router Manager..." >> "$LOG_FILE"

# Backup local changes if any
if [[ -n "$(git status --porcelain)" ]]; then
    echo "Backing up local changes..." >> "$LOG_FILE"
    git stash push -m "Auto-backup before update $(date)" >> "$LOG_FILE" 2>&1
fi

# Pull updates
git pull origin main >> "$LOG_FILE" 2>&1

# Restart services
echo "Restarting Router Manager service..." >> "$LOG_FILE"
systemctl restart router-manager >> "$LOG_FILE" 2>&1

echo "$(date): Router Manager updated successfully." >> "$LOG_FILE"
echo "Router Manager updated successfully!"

# Show new version
if [[ -f "$INSTALL_DIR/VERSION" ]]; then
    VERSION=$(cat "$INSTALL_DIR/VERSION")
    echo "Current version: $VERSION"
fi
EOF

    chmod +x /usr/local/bin/router-manager-update
    print_success "Update script created at /usr/local/bin/router-manager-update"
}

# Function to create systemd timer for automatic updates (optional)
create_update_timer() {
    print_status "Creating automatic update timer..."

    # Create update service
    cat > /etc/systemd/system/router-manager-update.service << 'EOF'
[Unit]
Description=Router Manager Update Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/router-manager-update
User=root
StandardOutput=journal
StandardError=journal
EOF

    # Create update timer (weekly)
    cat > /etc/systemd/system/router-manager-update.timer << 'EOF'
[Unit]
Description=Router Manager Update Timer
Requires=router-manager-update.service

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable timer (but don't start it automatically)
    systemctl daemon-reload
    print_success "Update timer created (disabled by default)"
    print_status "To enable automatic weekly updates: systemctl enable --now router-manager-update.timer"
}

# Function to show completion message
show_completion() {
    print_success "Router Manager git-based installation completed!"
    echo
    echo -e "${GREEN}Installation Summary:${NC}"
    echo -e "  • Repository: ${BLUE}$REPO_URL${NC}"
    echo -e "  • Installation Directory: ${BLUE}$INSTALL_DIR${NC}"
    echo -e "  • Version: ${BLUE}$(cat $INSTALL_DIR/VERSION 2>/dev/null || echo 'Unknown')${NC}"
    echo -e "  • Web Interface: ${BLUE}https://$(hostname -I | awk '{print $1}')${NC}"
    echo -e "  • Default Credentials: ${BLUE}admin / admin${NC}"
    echo
    echo -e "${YELLOW}Management Commands:${NC}"
    echo -e "  • Update: ${BLUE}router-manager-update${NC}"
    echo -e "  • Check version: ${BLUE}cat $INSTALL_DIR/VERSION${NC}"
    echo -e "  • Service status: ${BLUE}systemctl status router-manager${NC}"
    echo -e "  • View logs: ${BLUE}journalctl -u router-manager -f${NC}"
    echo
    echo -e "${YELLOW}Repository Commands:${NC}"
    echo -e "  • Check for updates: ${BLUE}cd $INSTALL_DIR && git fetch && git status${NC}"
    echo -e "  • Manual update: ${BLUE}cd $INSTALL_DIR && git pull${NC}"
    echo -e "  • View commit log: ${BLUE}cd $INSTALL_DIR && git log --oneline -n 10${NC}"
}

# Main installation function
main() {
    print_status "Starting Router Manager git-based installation..."
    echo "Installation log: $LOG_FILE"

    check_root
    detect_os
    install_git
    setup_repository
    run_installation
    create_update_script
    create_update_timer
    show_completion
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --repo-url URL    Git repository URL (default: $REPO_URL)"
            echo "  --branch BRANCH   Git branch to use (default: $BRANCH)"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"
