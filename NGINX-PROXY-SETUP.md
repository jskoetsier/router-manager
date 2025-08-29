# Nginx Proxy Manager Setup Guide

This guide explains how to set up and use the nginx proxy functionality in Router Manager, which provides a web-based interface for configuring nginx reverse proxies with automatic SSL certificate generation via Let's Encrypt.

## Features

- **Web-based Configuration**: Configure nginx reverse proxies through an intuitive web interface
- **Automatic SSL**: Generate and renew SSL certificates automatically using Let's Encrypt/Certbot
- **Multiple Deployment Options**: Deploy on bare metal, Docker, or container environments
- **Advanced Configuration**: Support for custom headers, rate limiting, timeouts, and security settings
- **Monitoring & Logging**: Track deployment history, certificate expiry, and nginx status
- **Quick Setup**: One-click proxy setup for simple configurations

## Architecture Overview

```
Internet → Nginx Proxy → Router Manager → Backend Applications
                ↓
        Let's Encrypt SSL Certificates
```

## Installation Options

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd router-manager
   ```

2. **Start the services**:
   ```bash
   # Start the complete stack with nginx proxy
   docker-compose -f docker-compose.nginx.yml up -d
   ```

3. **Access the web interface**:
   - Navigate to `http://localhost:8000` (or your server's IP)
   - Login with admin credentials (created during first startup)
   - Go to "Nginx Proxy" section

### Option 2: Bare Metal Installation

1. **Install system dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install nginx certbot python3-certbot-nginx postgresql redis-server

   # RHEL/CentOS
   sudo dnf install nginx certbot python3-certbot-nginx postgresql redis
   ```

2. **Set up the Django application**:
   ```bash
   cd router-manager/webapp
   pip install -r requirements.txt
   
   # Configure database settings in .env file
   cp .env.example .env
   
   # Run migrations
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py collectstatic
   ```

3. **Configure nginx directories**:
   ```bash
   sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
   sudo mkdir -p /var/www/certbot
   sudo chown -R www-data:www-data /var/www/certbot
   ```

4. **Start services**:
   ```bash
   # Start Router Manager
   python manage.py runserver 0.0.0.0:8000
   
   # Or use gunicorn for production
   gunicorn router_manager.wsgi:application --bind 0.0.0.0:8000
   ```

## Configuration

### Environment Variables

Configure the following environment variables for optimal setup:

```env
# Nginx Configuration
NGINX_CONFIG_DIR=/etc/nginx/sites-available
NGINX_ENABLED_DIR=/etc/nginx/sites-enabled
NGINX_BINARY=/usr/sbin/nginx
SYSTEMCTL_BINARY=/usr/bin/systemctl

# Let's Encrypt Configuration
CERTBOT_BINARY=/usr/bin/certbot
CERTBOT_WEBROOT_PATH=/var/www/certbot
LETSENCRYPT_DIR=/etc/letsencrypt
LETSENCRYPT_EMAIL=admin@yourdomain.com

# Docker Configuration (if using containers)
NGINX_CONTAINER_NAME=nginx-proxy
DOCKER_COMPOSE_FILE=docker-compose.nginx.yml
```

### Django Settings

Add to your Django settings:

```python
# Add nginx_mgr to INSTALLED_APPS
INSTALLED_APPS = [
    # ... other apps
    'nginx_mgr',
]

# Add nginx manager URLs
urlpatterns = [
    # ... other URLs
    path('nginx/', include('nginx_mgr.urls')),
]
```

## Usage

### Creating a Simple Proxy Configuration

1. **Access the Nginx Manager**:
   - Go to `/nginx/` in your Router Manager web interface
   - Click "Quick Create" for simple configurations

2. **Fill in basic details**:
   - **Name**: `my-app-proxy`
   - **Domain**: `myapp.example.com`
   - **Upstream Port**: `3000` (port where your app runs)
   - **Enable SSL**: ✓ (for automatic Let's Encrypt certificates)

3. **Deploy the configuration**:
   - Click "Create Proxy Configuration"
   - Click "Deploy" on the configuration detail page
   - Wait for SSL certificate generation (if enabled)

### Advanced Configuration

For more complex setups, use the full configuration form:

1. **Basic Settings**:
   - Configuration name and description
   - Domain name for the proxy

2. **SSL Settings**:
   - Enable/disable SSL
   - Automatic certificate generation
   - Force HTTPS redirects

3. **Upstream Configuration**:
   - Backend server host and port
   - Protocol (HTTP/HTTPS)

4. **Proxy Settings**:
   - Connection timeouts
   - Read/write timeouts
   - Custom headers

5. **Security Settings**:
   - Rate limiting (requests per minute)
   - Access and error logging

### Managing SSL Certificates

**Automatic Certificate Generation**:
- Certificates are automatically obtained when deploying with SSL enabled
- Certificates auto-renew every 12 hours via the certbot container

**Manual Certificate Renewal**:
```bash
# Renew specific certificate
docker exec router-manager-certbot certbot renew --cert-name example.com

# Renew all certificates
docker exec router-manager-certbot certbot renew
```

**Certificate Monitoring**:
- View certificate status in the web interface
- Get alerts for certificates expiring within 30 days
- Monitor renewal history in deployment logs

## File Structure

```
router-manager/
├── docker-compose.nginx.yml    # Docker Compose with nginx + certbot
├── nginx/                      # Nginx configuration files
│   ├── nginx.conf             # Main nginx configuration
│   ├── sites-available/       # Generated proxy configurations
│   ├── sites-enabled/         # Symlinks to enabled configurations
│   └── ssl/                   # SSL certificates and keys
├── webapp/nginx_mgr/          # Django app for nginx management
│   ├── models.py              # Database models
│   ├── views.py               # Web interface views
│   ├── forms.py               # Configuration forms
│   ├── utils.py               # Nginx and certbot managers
│   └── templates/             # HTML templates
└── docker/                    # Docker configuration
    ├── Dockerfile             # Application container
    └── entrypoint.sh          # Container startup script
```

## Security Considerations

### Production Deployment

1. **Firewall Configuration**:
   ```bash
   # Allow HTTP and HTTPS traffic
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   
   # Restrict Router Manager access
   sudo ufw allow from <your-ip> to any port 8000
   ```

2. **SSL Configuration**:
   - The nginx configuration uses modern TLS settings
   - HSTS headers are automatically added
   - Perfect Forward Secrecy is enabled

3. **Access Control**:
   - Only staff members can access nginx management
   - All actions are logged in deployment history
   - Configuration changes require authentication

### Docker Security

1. **Container Isolation**:
   - Services run in separate containers with minimal privileges
   - Nginx runs as non-root user where possible
   - Certificates are stored in protected volumes

2. **Network Security**:
   - Internal communication uses Docker networks
   - Only necessary ports are exposed to the host

## Troubleshooting

### Common Issues

**Nginx Configuration Test Failed**:
```bash
# Check nginx configuration manually
sudo nginx -t

# View nginx error logs
sudo tail -f /var/log/nginx/error.log
```

**SSL Certificate Generation Failed**:
```bash
# Check certbot logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log

# Verify DNS resolution
nslookup yourdomain.com

# Check firewall (port 80 must be open)
sudo ufw status
```

**Deployment Logs Show Errors**:
- Check the deployment logs in the web interface
- Verify upstream server is running and accessible
- Ensure domain DNS points to your server

### Docker Troubleshooting

**Container Issues**:
```bash
# Check container logs
docker logs router-manager-nginx
docker logs router-manager-certbot
docker logs router-manager-app

# Restart services
docker-compose -f docker-compose.nginx.yml restart
```

**Permission Issues**:
```bash
# Fix nginx configuration permissions
sudo chown -R www-data:www-data /path/to/nginx/configs

# Fix certbot webroot permissions
sudo chown -R www-data:www-data /var/www/certbot
```

## API Integration

The nginx manager provides REST API endpoints for programmatic access:

```python
import requests

# Get configuration status
response = requests.get('http://localhost:8000/nginx/api/configs/')

# Deploy a configuration
response = requests.post(
    'http://localhost:8000/nginx/api/configs/1/deploy/',
    headers={'Authorization': 'Token your-api-token'}
)
```

## Monitoring and Maintenance

### Health Checks

- Nginx status is monitored automatically
- Certificate expiry is tracked
- Deployment history is maintained
- System metrics are available via the dashboard

### Backup and Recovery

**Configuration Backup**:
```bash
# Backup nginx configurations
tar -czf nginx-backup.tar.gz /etc/nginx/sites-available/

# Backup SSL certificates
tar -czf ssl-backup.tar.gz /etc/letsencrypt/
```

**Database Backup**:
```bash
# PostgreSQL backup
pg_dump routermanager > backup.sql

# Restore
psql routermanager < backup.sql
```

## Advanced Usage

### Custom Nginx Templates

You can customize the nginx configuration template:

1. Edit `/webapp/templates/nginx_mgr/nginx_config.conf`
2. Add custom directives or modify existing ones
3. Redeploy configurations to apply changes

### Integration with CI/CD

Example GitLab CI pipeline for automatic deployment:

```yaml
deploy_proxy:
  script:
    - curl -X POST "$ROUTER_MANAGER_URL/nginx/api/configs/$CONFIG_ID/deploy/" \
           -H "Authorization: Token $API_TOKEN"
  only:
    - main
```

## Support

For issues and questions:

1. Check the deployment logs in the web interface
2. Review the troubleshooting section above
3. Check Docker/system logs for detailed error messages
4. Verify network connectivity and DNS resolution

## Contributing

To contribute to the nginx proxy functionality:

1. Follow the existing code structure in `webapp/nginx_mgr/`
2. Add tests for new features
3. Update documentation for any changes
4. Test with both Docker and bare metal deployments