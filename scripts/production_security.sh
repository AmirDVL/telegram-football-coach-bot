#!/bin/bash

# =================================================================
# TELEGRAM FOOTBALL COACH BOT - LINUX SECURITY HARDENING
# =================================================================
# Production security script for Linux servers
# Run with: chmod +x production_security.sh && sudo ./production_security.sh

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
   exit 1
fi

# Check if running on Linux
if [[ "$(uname -s)" != "Linux" ]]; then
    error "This script is only for Linux servers"
    exit 1
fi

# =================================================================
# SYSTEM SECURITY HARDENING
# =================================================================

harden_system_security() {
    log "🛡️  Hardening system security..."
    
    # Update system packages
    log "Updating system packages..."
    apt update && apt upgrade -y
    
    # Install security tools
    log "Installing security tools..."
    apt install -y ufw fail2ban htop net-tools
    
    # Configure UFW firewall
    log "Configuring UFW firewall..."
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 443/tcp
    ufw allow 80/tcp
    ufw --force enable
    
    success "System security hardened"
}

# =================================================================
# BOT USER AND PERMISSIONS
# =================================================================

setup_bot_user() {
    log "👤 Setting up bot user and permissions..."
    
    BOT_USER="telegram_bot"
    BOT_HOME="/home/$BOT_USER"
    BOT_DIR="/opt/telegram_bot"
    
    # Create bot user if not exists
    if ! id "$BOT_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$BOT_USER"
        log "Created user: $BOT_USER"
    fi
    
    # Create bot directory
    mkdir -p "$BOT_DIR"
    chown "$BOT_USER:$BOT_USER" "$BOT_DIR"
    chmod 750 "$BOT_DIR"
    
    # Set up directory structure
    mkdir -p "$BOT_DIR"/{logs,user_documents,questionnaire_photos,exports,backups}
    chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"
    chmod 700 "$BOT_DIR"/{logs,user_documents,questionnaire_photos,exports,backups}
    
    success "Bot user and directories configured"
}

# =================================================================
# FILE PERMISSIONS SECURITY
# =================================================================

secure_file_permissions() {
    log "🔐 Securing file permissions..."
    
    BOT_DIR="/opt/telegram_bot"
    BOT_USER="telegram_bot"
    
    cd "$BOT_DIR" || exit 1
    
    # Secure Python files
    find . -name "*.py" -exec chmod 644 {} \;
    chmod 755 main.py  # Main entry point executable
    
    # Secure configuration files
    if [[ -f ".env" ]]; then
        chmod 600 .env
        chown "$BOT_USER:$BOT_USER" .env
    fi
    
    # Secure data files
    find . -name "*.json" -exec chmod 600 {} \;
    
    # Secure directories
    find . -type d -exec chmod 750 {} \;
    chmod 700 logs/ user_documents/ questionnaire_photos/ exports/ backups/ 2>/dev/null || true
    
    # Set ownership
    chown -R "$BOT_USER:$BOT_USER" .
    
    success "File permissions secured"
}

# =================================================================
# FAIL2BAN CONFIGURATION
# =================================================================

setup_fail2ban() {
    log "🚫 Configuring Fail2ban..."
    
    # Create custom fail2ban filter for bot abuse
    cat > /etc/fail2ban/filter.d/telegram-bot.conf << 'EOF'
[Definition]
failregex = \[ERROR\].*Bot.*abuse.*from.*<HOST>
            \[WARNING\].*Suspicious.*activity.*from.*<HOST>
            \[CRITICAL\].*Security.*violation.*from.*<HOST>
ignoreregex =
EOF

    # Create jail configuration
    cat > /etc/fail2ban/jail.d/telegram-bot.conf << 'EOF'
[telegram-bot]
enabled = true
port = http,https,ssh
filter = telegram-bot
logpath = /opt/telegram_bot/logs/*.log
maxretry = 3
bantime = 3600
findtime = 600
EOF

    # Restart fail2ban
    systemctl restart fail2ban
    systemctl enable fail2ban
    
    success "Fail2ban configured"
}

# =================================================================
# SYSTEMD SERVICE HARDENING
# =================================================================

create_hardened_service() {
    log "⚙️  Creating hardened systemd service..."
    
    BOT_USER="telegram_bot"
    BOT_DIR="/opt/telegram_bot"
    
    cat > /etc/systemd/system/telegram-football-bot.service << EOF
[Unit]
Description=Telegram Football Coach Bot
After=network.target network-online.target
Wants=network-online.target
StartLimitBurst=3
StartLimitIntervalSec=60

[Service]
Type=simple
User=$BOT_USER
Group=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment=PATH=$BOT_DIR/venv_prod/bin
ExecStart=$BOT_DIR/venv_prod/bin/python $BOT_DIR/main.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
TimeoutStartSec=30
TimeoutStopSec=10

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
RestrictNamespaces=yes
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# File system access
ReadWritePaths=$BOT_DIR
ReadOnlyPaths=/etc/ssl/certs
InaccessiblePaths=/home /root /opt

# Capabilities
CapabilityBoundingSet=
AmbientCapabilities=

# Resource limits
LimitNOFILE=1024
LimitNPROC=512
MemoryMax=512M
CPUQuota=50%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-football-bot

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable telegram-football-bot
    
    success "Hardened systemd service created"
}

# =================================================================
# LOG ROTATION
# =================================================================

setup_log_rotation() {
    log "📝 Setting up log rotation..."
    
    cat > /etc/logrotate.d/telegram-bot << 'EOF'
/opt/telegram_bot/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    create 640 telegram_bot telegram_bot
    postrotate
        systemctl reload telegram-football-bot > /dev/null 2>&1 || true
    endscript
}
EOF

    success "Log rotation configured"
}

# =================================================================
# MONITORING SCRIPT
# =================================================================

create_monitoring_script() {
    log "📊 Creating monitoring script..."
    
    cat > /opt/telegram_bot/security_monitor.sh << 'EOF'
#!/bin/bash

# Security monitoring for Telegram Football Coach Bot
LOG_FILE="/var/log/telegram-bot-security.log"
BOT_DIR="/opt/telegram_bot"

# Function to log with timestamp
log_security() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check service status
SERVICE_STATUS=$(systemctl is-active telegram-football-bot)
if [[ "$SERVICE_STATUS" != "active" ]]; then
    log_security "ALERT: Bot service is not running - Status: $SERVICE_STATUS"
fi

# Check file permissions
if [[ -f "$BOT_DIR/.env" ]]; then
    ENV_PERMS=$(stat -c "%a" "$BOT_DIR/.env")
    if [[ "$ENV_PERMS" != "600" ]]; then
        log_security "SECURITY: .env file has incorrect permissions: $ENV_PERMS"
        chmod 600 "$BOT_DIR/.env"
    fi
fi

# Check for suspicious files
find "$BOT_DIR" -name "*.tmp" -o -name "*.backup" -o -name "core.*" | while read file; do
    log_security "WARNING: Suspicious file found: $file"
done

# Check disk space
DISK_USAGE=$(df -h "$BOT_DIR" | awk 'NR==2{print $5}' | sed 's/%//')
if [[ $DISK_USAGE -gt 85 ]]; then
    log_security "WARNING: High disk usage: ${DISK_USAGE}%"
fi

# Check memory usage
BOT_PID=$(pgrep -f "python.*main.py")
if [[ -n "$BOT_PID" ]]; then
    MEM_USAGE=$(ps -p "$BOT_PID" -o %mem --no-headers | tr -d ' ')
    if (( $(echo "$MEM_USAGE > 20" | bc -l) )); then
        log_security "WARNING: High memory usage by bot: ${MEM_USAGE}%"
    fi
fi

# Check for failed login attempts in bot logs
if [[ -d "$BOT_DIR/logs" ]]; then
    FAILED_ATTEMPTS=$(grep -c "WARNING.*Non-admin.*attempted" "$BOT_DIR/logs"/*.log 2>/dev/null || echo 0)
    if [[ $FAILED_ATTEMPTS -gt 5 ]]; then
        log_security "SECURITY: Multiple non-admin access attempts: $FAILED_ATTEMPTS"
    fi
fi
EOF

    chmod +x /opt/telegram_bot/security_monitor.sh
    chown telegram_bot:telegram_bot /opt/telegram_bot/security_monitor.sh
    
    # Add to crontab for telegram_bot user
    (crontab -u telegram_bot -l 2>/dev/null; echo "*/10 * * * * /opt/telegram_bot/security_monitor.sh") | crontab -u telegram_bot -
    
    success "Security monitoring configured"
}

# =================================================================
# MAIN EXECUTION
# =================================================================

main() {
    echo -e "${PURPLE}"
    echo "================================================================="
    echo "  TELEGRAM FOOTBALL COACH BOT - LINUX SECURITY HARDENING"
    echo "================================================================="
    echo -e "${NC}"
    echo "🛡️  Implementing production security measures..."
    echo ""
    
    harden_system_security
    setup_bot_user
    secure_file_permissions
    setup_fail2ban
    create_hardened_service
    setup_log_rotation
    create_monitoring_script
    
    echo ""
    echo -e "${GREEN}"
    echo "================================================================="
    echo "  🎉 LINUX SECURITY HARDENING COMPLETE!"
    echo "================================================================="
    echo -e "${NC}"
    echo "🔒 Security Features Implemented:"
    echo "• UFW firewall with minimal ports"
    echo "• Fail2ban protection against abuse"
    echo "• Hardened systemd service with security restrictions"
    echo "• Proper file permissions and ownership"
    echo "• Log rotation and monitoring"
    echo "• Resource limits and sandboxing"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Deploy bot files to /opt/telegram_bot/"
    echo "2. Configure .env with production values"
    echo "3. Start service: systemctl start telegram-football-bot"
    echo "4. Monitor logs: journalctl -u telegram-football-bot -f"
    echo ""
    success "Linux production security hardening completed!"
}

main "$@"
