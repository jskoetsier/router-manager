import os
import subprocess
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from .models import SSLCertificate

logger = logging.getLogger(__name__)


class NginxManager:
    """Manages nginx configuration and operations"""

    def __init__(self):
        self.nginx_config_dir = getattr(settings, 'NGINX_CONFIG_DIR', '/etc/nginx/sites-available')
        self.nginx_enabled_dir = getattr(settings, 'NGINX_ENABLED_DIR', '/etc/nginx/sites-enabled')
        self.nginx_binary = getattr(settings, 'NGINX_BINARY', '/usr/sbin/nginx')
        self.systemctl_binary = getattr(settings, 'SYSTEMCTL_BINARY', '/usr/bin/systemctl')

    def deploy_config(self, proxy_config):
        """Deploy nginx configuration for a proxy config"""
        try:
            # Generate nginx configuration
            config_content = self._generate_config(proxy_config)

            # Write configuration file
            config_filename = f"{proxy_config.name}.conf"
            config_path = os.path.join(self.nginx_config_dir, config_filename)

            with open(config_path, 'w') as f:
                f.write(config_content)

            # Enable the site by creating symlink
            enabled_path = os.path.join(self.nginx_enabled_dir, config_filename)
            if not os.path.exists(enabled_path):
                os.symlink(config_path, enabled_path)

            # Test nginx configuration
            if not self.test_config():
                return False, "Nginx configuration test failed"

            # Reload nginx
            if not self.reload():
                return False, "Failed to reload nginx"

            logger.info(f"Deployed nginx configuration for {proxy_config.name}")
            return True, f"Successfully deployed configuration for {proxy_config.domain_name}"

        except Exception as e:
            logger.error(f"Failed to deploy nginx config for {proxy_config.name}: {e}")
            return False, str(e)

    def remove_config(self, proxy_config):
        """Remove nginx configuration for a proxy config"""
        try:
            config_filename = f"{proxy_config.name}.conf"

            # Remove enabled symlink
            enabled_path = os.path.join(self.nginx_enabled_dir, config_filename)
            if os.path.exists(enabled_path):
                os.remove(enabled_path)

            # Remove configuration file
            config_path = os.path.join(self.nginx_config_dir, config_filename)
            if os.path.exists(config_path):
                os.remove(config_path)

            # Reload nginx
            self.reload()

            logger.info(f"Removed nginx configuration for {proxy_config.name}")
            return True, f"Successfully removed configuration for {proxy_config.domain_name}"

        except Exception as e:
            logger.error(f"Failed to remove nginx config for {proxy_config.name}: {e}")
            return False, str(e)

    def _generate_config(self, proxy_config):
        """Generate nginx configuration content"""
        context = {
            'config': proxy_config,
            'ssl_cert_path': f'/etc/letsencrypt/live/{proxy_config.domain_name}/fullchain.pem',
            'ssl_key_path': f'/etc/letsencrypt/live/{proxy_config.domain_name}/privkey.pem',
        }

        return render_to_string('nginx_mgr/nginx_config.conf', context)

    def test_config(self):
        """Test nginx configuration"""
        try:
            result = subprocess.run(
                [self.nginx_binary, '-t'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to test nginx config: {e}")
            return False

    def reload(self):
        """Reload nginx configuration"""
        try:
            result = subprocess.run(
                [self.systemctl_binary, 'reload', 'nginx'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to reload nginx: {e}")
            return False

    def restart(self):
        """Restart nginx service"""
        try:
            result = subprocess.run(
                [self.systemctl_binary, 'restart', 'nginx'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to restart nginx: {e}")
            return False

    def is_running(self):
        """Check if nginx is running"""
        try:
            result = subprocess.run(
                [self.systemctl_binary, 'is-active', 'nginx'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and result.stdout.strip() == 'active'
        except Exception as e:
            logger.error(f"Failed to check nginx status: {e}")
            return False

    def get_status(self):
        """Get detailed nginx status"""
        return {
            'running': self.is_running(),
            'config_valid': self.test_config(),
            'version': self.get_version(),
        }

    def get_version(self):
        """Get nginx version"""
        try:
            result = subprocess.run(
                [self.nginx_binary, '-v'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # nginx outputs version to stderr
                version_line = result.stderr.strip()
                if 'nginx/' in version_line:
                    return version_line.split('nginx/')[1].split()[0]
            return "Unknown"
        except Exception as e:
            logger.error(f"Failed to get nginx version: {e}")
            return "Unknown"


class CertbotManager:
    """Manages SSL certificates via certbot/Let's Encrypt"""

    def __init__(self):
        self.certbot_binary = getattr(settings, 'CERTBOT_BINARY', '/usr/bin/certbot')
        self.webroot_path = getattr(settings, 'CERTBOT_WEBROOT_PATH', '/var/www/certbot')
        self.letsencrypt_dir = getattr(settings, 'LETSENCRYPT_DIR', '/etc/letsencrypt')

    def obtain_certificate(self, proxy_config):
        """Obtain SSL certificate for a domain"""
        try:
            domain = proxy_config.domain_name

            # Ensure webroot directory exists
            os.makedirs(self.webroot_path, exist_ok=True)

            # Run certbot to obtain certificate
            cmd = [
                self.certbot_binary,
                'certonly',
                '--webroot',
                '--webroot-path', self.webroot_path,
                '-d', domain,
                '--non-interactive',
                '--agree-tos',
                '--email', self._get_admin_email(),
                '--no-eff-email'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0:
                # Create or update SSL certificate record
                self._save_certificate_info(proxy_config, domain)

                logger.info(f"Successfully obtained SSL certificate for {domain}")
                return True, f"SSL certificate obtained for {domain}"
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Failed to obtain SSL certificate for {domain}: {error_msg}")
                return False, f"Certbot failed: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Certificate request timed out"
        except Exception as e:
            logger.error(f"Failed to obtain certificate for {proxy_config.domain_name}: {e}")
            return False, str(e)

    def renew_certificate(self, proxy_config):
        """Renew SSL certificate for a domain"""
        try:
            domain = proxy_config.domain_name

            cmd = [
                self.certbot_binary,
                'renew',
                '--cert-name', domain,
                '--non-interactive'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                # Update certificate info
                self._save_certificate_info(proxy_config, domain)

                logger.info(f"Successfully renewed SSL certificate for {domain}")
                return True, f"SSL certificate renewed for {domain}"
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Failed to renew SSL certificate for {domain}: {error_msg}")
                return False, f"Renewal failed: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Certificate renewal timed out"
        except Exception as e:
            logger.error(f"Failed to renew certificate for {proxy_config.domain_name}: {e}")
            return False, str(e)

    def renew_all_certificates(self):
        """Renew all certificates"""
        try:
            cmd = [
                self.certbot_binary,
                'renew',
                '--non-interactive',
                '--quiet'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to renew all certificates: {e}")
            return False

    def _save_certificate_info(self, proxy_config, domain):
        """Save or update SSL certificate information in database"""
        try:
            cert_dir = os.path.join(self.letsencrypt_dir, 'live', domain)

            if not os.path.exists(cert_dir):
                raise Exception(f"Certificate directory not found: {cert_dir}")

            # Get certificate expiry date
            cert_path = os.path.join(cert_dir, 'fullchain.pem')
            expiry_date = self._get_certificate_expiry(cert_path)

            # Create or update SSL certificate record
            ssl_cert, created = SSLCertificate.objects.get_or_create(
                proxy_config=proxy_config,
                defaults={
                    'certificate_path': cert_path,
                    'private_key_path': os.path.join(cert_dir, 'privkey.pem'),
                    'fullchain_path': cert_path,
                    'issued_date': timezone.now(),
                    'expiry_date': expiry_date,
                }
            )

            if not created:
                # Update existing record
                ssl_cert.certificate_path = cert_path
                ssl_cert.private_key_path = os.path.join(cert_dir, 'privkey.pem')
                ssl_cert.fullchain_path = cert_path
                ssl_cert.expiry_date = expiry_date
                ssl_cert.is_valid = True
                ssl_cert.save()

        except Exception as e:
            logger.error(f"Failed to save certificate info for {domain}: {e}")

    def _get_certificate_expiry(self, cert_path):
        """Get certificate expiry date"""
        try:
            cmd = [
                'openssl', 'x509', '-in', cert_path, '-noout', '-enddate'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parse output: notAfter=Jan  1 00:00:00 2024 GMT
                date_str = result.stdout.strip().split('=')[1]
                expiry_date = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                return timezone.make_aware(expiry_date)

        except Exception as e:
            logger.error(f"Failed to get certificate expiry for {cert_path}: {e}")

        # Fallback: assume 90 days from now (Let's Encrypt default)
        return timezone.now() + timedelta(days=90)

    def _get_admin_email(self):
        """Get admin email for Let's Encrypt registration"""
        # You can configure this in settings or get from user model
        return getattr(settings, 'LETSENCRYPT_EMAIL', 'admin@localhost')

    def get_status(self):
        """Get certbot status"""
        try:
            result = subprocess.run(
                [self.certbot_binary, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            available = result.returncode == 0
            version = "Unknown"

            if available and result.stdout:
                # Extract version from output
                version_line = result.stdout.strip()
                if 'certbot' in version_line:
                    version = version_line.split()[1]

            return {
                'available': available,
                'version': version,
            }

        except Exception as e:
            logger.error(f"Failed to get certbot status: {e}")
            return {
                'available': False,
                'version': "Unknown",
            }


class DockerNginxManager:
    """Alternative nginx manager for Docker environments"""

    def __init__(self):
        self.container_name = getattr(settings, 'NGINX_CONTAINER_NAME', 'nginx-proxy')
        self.docker_compose_file = getattr(settings, 'DOCKER_COMPOSE_FILE', 'docker-compose.yml')

    def deploy_config(self, proxy_config):
        """Deploy configuration in Docker environment"""
        try:
            # This would generate docker-compose configuration
            # and restart the nginx container
            pass
        except Exception as e:
            return False, str(e)

    def reload(self):
        """Reload nginx in Docker container"""
        try:
            result = subprocess.run(
                ['docker', 'exec', self.container_name, 'nginx', '-s', 'reload'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to reload nginx container: {e}")
            return False
