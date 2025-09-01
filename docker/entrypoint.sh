u#!/bin/bash

set -e

echo "Starting Router Manager with nginx proxy support..."

# Wait for database to be ready
echo "Waiting for database connection..."
while ! python manage.py check --database default > /dev/null 2>&1; do
    echo "Database not ready, waiting..."
    sleep 2
done
echo "Database connection established!"

# Run Django migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create nginx configuration directories if they don't exist
mkdir -p /nginx-configs/sites-available /nginx-configs/sites-enabled

# Generate DH parameters if they don't exist (for SSL)
if [ ! -f "/etc/ssl/certs/dhparam.pem" ]; then
    echo "Generating DH parameters (this may take a while)..."
    openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048 &
fi

# Set up Let's Encrypt webroot
mkdir -p /var/www/certbot

# Start the application
echo "Starting Django application server..."
exec gunicorn router_manager.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile /var/log/router-manager/access.log \
    --error-logfile /var/log/router-manager/error.log \
    --log-level info
