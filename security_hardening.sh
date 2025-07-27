#!/bin/bash
# security_setup.sh - Automated Security Setup Script

set -e

echo "🔒 Football Coach Bot - Security Setup Script"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

echo ""
print_info "Starting security hardening process..."
echo ""

# 1. Secure PostgreSQL Configuration
print_info "Step 1: Securing PostgreSQL Configuration"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL is not installed. Please install it first."
    exit 1
fi

# Backup original configuration files
print_info "Backing up original PostgreSQL configuration..."
sudo cp /etc/postgresql/*/main/postgresql.conf /etc/postgresql/*/main/postgresql.conf.backup.$(date +%Y%m%d)
sudo cp /etc/postgresql/*/main/pg_hba.conf /etc/postgresql/*/main/pg_hba.conf.backup.$(date +%Y%m%d)

print_status "PostgreSQL configuration backed up"

# Apply secure PostgreSQL settings
print_info "Applying secure PostgreSQL configuration..."

# Update postgresql.conf
sudo tee -a /etc/postgresql/*/main/postgresql.conf.security > /dev/null <<EOF

# Security Settings Added by Football Coach Bot Setup
listen_addresses = 'localhost'
ssl = on
password_encryption = scram-sha-256
log_connections = on
log_disconnections = on
log_statement = 'mod'
shared_preload_libraries = 'pg_stat_statements'
max_connections = 100
EOF

# Update pg_hba.conf for secure authentication
sudo tee /etc/postgresql/*/main/pg_hba.conf.secure > /dev/null <<EOF
# Secure pg_hba.conf for Football Coach Bot
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             all                                     scram-sha-256

# IPv4 local connections (secure)
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections (secure)  
host    all             all             ::1/128                 scram-sha-256

# Reject all other connections
host    all             all             0.0.0.0/0               reject
EOF

# Apply the secure configuration
sudo cp /etc/postgresql/*/main/postgresql.conf.security /etc/postgresql/*/main/postgresql.conf
sudo cp /etc/postgresql/*/main/pg_hba.conf.secure /etc/postgresql/*/main/pg_hba.conf

print_status "PostgreSQL configuration secured"

# 2. Set up fail2ban
print_info "Step 2: Installing and configuring fail2ban"

if ! command -v fail2ban-client &> /dev/null; then
    print_info "Installing fail2ban..."
    sudo apt update
    sudo apt install -y fail2ban
fi

# Configure fail2ban for PostgreSQL
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[postgresql]
enabled = true
port = 5432
filter = postgresql
logpath = /var/log/postgresql/postgresql-*-main.log
maxretry = 3
bantime = 3600
EOF

# Create PostgreSQL fail2ban filter
sudo tee /etc/fail2ban/filter.d/postgresql.conf > /dev/null <<EOF
[Definition]
failregex = %(__prefix_line)s.*FATAL:.*authentication failed for user.*
            %(__prefix_line)s.*FATAL:.*password authentication failed.*
            %(__prefix_line)s.*FATAL:.*no pg_hba.conf entry.*
ignoreregex =
EOF

sudo systemctl enable fail2ban
sudo systemctl restart fail2ban

print_status "fail2ban installed and configured"

# 3. Secure file permissions
print_info "Step 3: Setting secure file permissions"

# Set restrictive permissions on bot directory
chmod 750 /opt/football-bot
chmod 600 /opt/football-bot/.env
chmod 644 /opt/football-bot/*.py
chmod 755 /opt/football-bot/venv/bin/*

# Create logs directory with secure permissions
sudo mkdir -p /var/log/football-bot
sudo chown footballbot:footballbot /var/log/football-bot
sudo chmod 750 /var/log/football-bot

print_status "File permissions secured"

# 4. Set up log rotation
print_info "Step 4: Configuring log rotation"

sudo tee /etc/logrotate.d/football-bot > /dev/null <<EOF
/var/log/football-bot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 footballbot footballbot
    postrotate
        systemctl reload football-bot > /dev/null 2>&1 || true
    endscript
}

/opt/football-bot/security.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    create 0600 footballbot footballbot
}
EOF

print_status "Log rotation configured"

# 5. Firewall configuration
print_info "Step 5: Configuring firewall"

sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow from 127.0.0.1 to any port 5432

print_status "Firewall configured"

# 6. Create backup script
print_info "Step 6: Setting up automated backups"

sudo tee /opt/football-bot/secure_backup.sh > /dev/null <<'EOF'
#!/bin/bash

# Secure backup script for Football Coach Bot
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/football-bot/backups"
DB_NAME="football_coach_bot"
DB_USER="footballbot_app"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

# Create application backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    /opt/football-bot/

echo "Backup completed: $DATE"
EOF

chmod +x /opt/football-bot/secure_backup.sh
chown footballbot:footballbot /opt/football-bot/secure_backup.sh

# Add backup to crontab
(crontab -u footballbot -l 2>/dev/null; echo "0 2 * * * /opt/football-bot/secure_backup.sh >> /opt/football-bot/backup.log 2>&1") | crontab -u footballbot -

print_status "Automated backups configured"

# 7. Security monitoring setup
print_info "Step 7: Setting up security monitoring"

# Create security monitoring systemd service
sudo tee /etc/systemd/system/football-bot-security.service > /dev/null <<EOF
[Unit]
Description=Football Coach Bot Security Monitor
After=network.target postgresql.service

[Service]
Type=simple
User=footballbot
Group=footballbot
WorkingDirectory=/opt/football-bot
Environment=PATH=/opt/football-bot/venv/bin
ExecStart=/opt/football-bot/venv/bin/python security_monitor.py monitor 300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable football-bot-security

print_status "Security monitoring configured"

# 8. Restart services
print_info "Step 8: Restarting services with secure configuration"

sudo systemctl restart postgresql
sudo systemctl restart fail2ban
sudo systemctl restart football-bot
sudo systemctl start football-bot-security

print_status "All services restarted with secure configuration"

# 9. Security validation
print_info "Step 9: Running security validation"

# Test database connection
if sudo -u footballbot psql -h localhost -U footballbot_app -d football_coach_bot -c "SELECT version();" > /dev/null 2>&1; then
    print_status "Database connection test passed"
else
    print_error "Database connection test failed"
fi

# Check fail2ban status
if sudo fail2ban-client status > /dev/null 2>&1; then
    print_status "fail2ban is running"
else
    print_error "fail2ban is not running"
fi

# Check firewall status
if sudo ufw status | grep -q "Status: active"; then
    print_status "Firewall is active"
else
    print_warning "Firewall is not active"
fi

# 10. Generate security report
print_info "Step 10: Generating initial security report"

sudo -u footballbot /opt/football-bot/venv/bin/python /opt/football-bot/security_monitor.py check

print_status "Initial security report generated"

echo ""
echo "=============================================="
print_status "Security hardening completed successfully!"
echo ""
print_info "IMPORTANT SECURITY NOTES:"
echo "• Database password: Use the secure password from your .env file"
echo "• Backup location: /opt/football-bot/backups/"
echo "• Security logs: /var/log/football-bot/ and /opt/football-bot/security.log"
echo "• Security monitoring: Service 'football-bot-security' is now running"
echo "• Daily backups: Automated at 2:00 AM"
echo ""
print_info "NEXT STEPS:"
echo "1. Test your bot: sudo systemctl status football-bot"
echo "2. Check security logs: tail -f /opt/football-bot/security.log"
echo "3. Monitor security: sudo systemctl status football-bot-security"
echo "4. View fail2ban status: sudo fail2ban-client status"
echo ""
print_warning "IMPORTANT: Keep your .env file secure and never commit it to version control!"
echo ""
