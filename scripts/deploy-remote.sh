#!/bin/bash

# Router Manager Remote Deployment Script
# This script deploys Router Manager to a remote server using git

set -euo pipefail

# Default configuration
REMOTE_HOST="192.168.1.253"
REMOTE_USER="root"
REMOTE_PORT="22"
REPO_URL="https://github.com/jskoetsier/router-manager.git"
BRANCH="main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if SSH connection works
check_ssh_connection() {
    print_status "Testing SSH connection to $REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT..."
    
    if ssh -p "$REMOTE_PORT" -o ConnectTimeout=5 -o BatchMode=yes "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH connection successful'" &>/dev/null; then
        print_success "SSH connection established"
    else
        print_error "Cannot establish SSH connection to $REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT"
        print_error "Please ensure:"
        print_error "  1. The remote host is reachable on port $REMOTE_PORT"
        print_error "  2. SSH key authentication is set up"
        print_error "  3. The remote user has sudo/root privileges"
        exit 1
    fi
}

# Function to check remote OS compatibility
check_remote_os() {
    print_status "Checking remote operating system..."
    
    OS_INFO=$(ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "cat /etc/os-release" 2>/dev/null || echo "")
    
    if echo "$OS_INFO" | grep -q 'ID="rocky"' && echo "$OS_INFO" | grep -q 'VERSION_ID="9'; then
        print_success "Rocky Linux 9 detected on remote host"
        REMOTE_OS="rocky9"
    elif echo "$OS_INFO" | grep -q 'ID="rhel"' && echo "$OS_INFO" | grep -q 'VERSION_ID="9'; then
        print_success "RHEL 9 detected on remote host"
        REMOTE_OS="rhel9"
    else
        print_error "Unsupported operating system on remote host"
        print_error "This deployment script supports Rocky Linux 9 and RHEL 9 only"
        echo "Remote OS info:"
        echo "$OS_INFO"
        exit 1
    fi
}

# Function to install git on remote host if needed
install_git_remote() {
    print_status "Checking if git is installed on remote host..."
    
    if ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "command -v git &>/dev/null"; then
        print_success "Git is already installed on remote host"
    else
        print_status "Installing git on remote host..."
        ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "dnf install -y git" || {
            print_error "Failed to install git on remote host"
            exit 1
        }
        print_success "Git installed on remote host"
    fi
}

# Function to clone or update repository on remote host
setup_repository_remote() {
    print_status "Setting up Router Manager repository on remote host..."
    
    # Check if repository already exists
    if ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "test -d /opt/router-manager/.git"; then
        print_status "Repository exists on remote host, updating..."
        
        # Update repository
        ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "
            cd /opt/router-manager
            # Backup any local changes
            if [[ -n \"\$(git status --porcelain)\" ]]; then
                echo 'Backing up local changes...'
                git stash push -m 'Auto-backup before deployment $(date)'
            fi
            
            # Update repository
            git fetch origin
            git checkout $BRANCH
            git pull origin $BRANCH
            
            echo 'Repository updated successfully'
        " || {
            print_error "Failed to update repository on remote host"
            exit 1
        }
        
        print_success "Repository updated on remote host"
    else
        print_status "Cloning repository to remote host..."
        
        # Remove existing directory if it exists but is not a git repo
        ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "
            if [[ -d /opt/router-manager ]]; then
                echo 'Removing existing non-git directory'
                rm -rf /opt/router-manager
            fi
        "
        
        # Clone repository
        ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "
            git clone $REPO_URL /opt/router-manager
            cd /opt/router-manager
            git checkout $BRANCH
        " || {
            print_error "Failed to clone repository on remote host"
            exit 1
        }
        
        print_success "Repository cloned to remote host"
    fi
    
    # Show current version
    VERSION=$(ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "cat /opt/router-manager/VERSION 2>/dev/null" || echo "Unknown")
    print_success "Router Manager version on remote host: $VERSION"
}

# Function to run installation on remote host
run_installation_remote() {
    print_status "Running Router Manager installation on remote host..."
    
    ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "
        cd /opt/router-manager
        chmod +x scripts/install-from-git.sh
        ./scripts/install-from-git.sh --repo-url $REPO_URL --branch $BRANCH
    " || {
        print_error "Installation failed on remote host"
        print_error "Check the installation logs on the remote host: /var/log/router-manager-install.log"
        exit 1
    }
    
    print_success "Router Manager installation completed on remote host"
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation on remote host..."
    
    # Check if service is running
    if ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "systemctl is-active router-manager &>/dev/null"; then
        print_success "Router Manager service is running"
    else
        print_warning "Router Manager service is not running, attempting to start..."
        ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "systemctl start router-manager" || {
            print_error "Failed to start Router Manager service"
            return 1
        }
    fi
    
    # Check web interface accessibility
    REMOTE_IP=$(ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "hostname -I | awk '{print \$1}'" 2>/dev/null || echo "$REMOTE_HOST")
    
    print_status "Testing web interface accessibility..."
    if curl -k -s "https://$REMOTE_IP" --connect-timeout 10 &>/dev/null; then
        print_success "Web interface is accessible at https://$REMOTE_IP"
    else
        print_warning "Web interface test failed - this might be normal if firewall rules are strict"
        print_status "Manual verification: try accessing https://$REMOTE_IP in your browser"
    fi
}

# Function to show deployment summary
show_deployment_summary() {
    REMOTE_IP=$(ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "hostname -I | awk '{print \$1}'" 2>/dev/null || echo "$REMOTE_HOST")
    VERSION=$(ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "cat /opt/router-manager/VERSION 2>/dev/null" || echo "Unknown")
    
    print_success "Router Manager deployment completed!"
    echo
    echo -e "${GREEN}Deployment Summary:${NC}"
    echo -e "  • Remote Host: ${BLUE}$REMOTE_USER@$REMOTE_HOST${NC}"
    echo -e "  • Repository: ${BLUE}$REPO_URL${NC}"
    echo -e "  • Branch: ${BLUE}$BRANCH${NC}"
    echo -e "  • Version: ${BLUE}$VERSION${NC}"
    echo -e "  • Web Interface: ${BLUE}https://$REMOTE_IP${NC}"
    echo -e "  • Default Credentials: ${BLUE}admin / admin${NC}"
    echo
    echo -e "${YELLOW}Remote Management Commands:${NC}"
    echo -e "  • Service status: ${BLUE}ssh $REMOTE_USER@$REMOTE_HOST systemctl status router-manager${NC}"
    echo -e "  • View logs: ${BLUE}ssh $REMOTE_USER@$REMOTE_HOST journalctl -u router-manager -f${NC}"
    echo -e "  • Update: ${BLUE}ssh $REMOTE_USER@$REMOTE_HOST /usr/local/bin/router-manager-update${NC}"
    echo -e "  • Check version: ${BLUE}ssh $REMOTE_USER@$REMOTE_HOST cat /opt/router-manager/VERSION${NC}"
    echo
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Access the web interface using the URL above"
    echo "  2. Login with default credentials (admin/admin)"
    echo "  3. Change the default password"
    echo "  4. Configure your router settings"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Deploy Router Manager to a remote server using git"
    echo
    echo "Options:"
    echo "  --host HOST       Remote host IP or hostname (default: $REMOTE_HOST)"
    echo "  --user USER       Remote SSH user (default: $REMOTE_USER)"
    echo "  --port PORT       Remote SSH port (default: $REMOTE_PORT)"
    echo "  --repo-url URL    Git repository URL (default: $REPO_URL)"
    echo "  --branch BRANCH   Git branch to deploy (default: $BRANCH)"
    echo "  --help, -h        Show this help message"
    echo
    echo "Examples:"
    echo "  $0                                              # Deploy to default host"
    echo "  $0 --host 10.0.0.100                          # Deploy to specific host"
    echo "  $0 --host 10.0.0.100 --user admin             # Deploy with specific user"
    echo "  $0 --host 10.0.0.100 --port 22123             # Deploy with custom SSH port"
    echo "  $0 --branch develop                            # Deploy from develop branch"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            REMOTE_HOST="$2"
            shift 2
            ;;
        --user)
            REMOTE_USER="$2"
            shift 2
            ;;
        --port)
            REMOTE_PORT="$2"
            shift 2
            ;;
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main deployment function
main() {
    print_status "Starting Router Manager remote deployment..."
    echo
    echo -e "${BLUE}Deployment Configuration:${NC}"
    echo -e "  • Remote Host: ${BLUE}$REMOTE_USER@$REMOTE_HOST${NC}"
    echo -e "  • Repository: ${BLUE}$REPO_URL${NC}"
    echo -e "  • Branch: ${BLUE}$BRANCH${NC}"
    echo
    
    check_ssh_connection
    check_remote_os
    install_git_remote
    setup_repository_remote
    run_installation_remote
    verify_installation
    show_deployment_summary
}

# Run main function
main "$@"