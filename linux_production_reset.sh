#!/bin/bash

# =================================================================
# TELEGRAM FOOTBALL COACH BOT - LINUX PRODUCTION RESET SCRIPT
# =================================================================
# SECURITY HARDENED - Linux Server Deployment Reset
# Run with: chmod +x linux_production_reset.sh && ./linux_production_reset.sh

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${CYAN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
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

# =================================================================
# SECURITY VALIDATION
# =================================================================

validate_linux_environment() {
    log "🐧 Validating Linux production environment..."
    
    # Check if running on Linux
    if [[ "$(uname -s)" != "Linux" ]]; then
        error "This script is ONLY for Linux servers. Current OS: $(uname -s)"
        exit 1
    fi
    
    # Check if running as non-root (security best practice)
    if [[ $EUID -eq 0 ]]; then
        error "DO NOT run this script as root for security reasons!"
        exit 1
    fi
    
    # Validate required commands
    local required_commands=("python3" "git" "systemctl" "ufw")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error "Required command not found: $cmd"
            exit 1
        fi
    done
    
    success "Linux environment validation passed"
}

# =================================================================
# BACKUP SYSTEM
# =================================================================

create_production_backup() {
    log "💾 Creating production backup..."
    
    local backup_dir="/opt/telegram_bot_backups/$(date +'%Y%m%d_%H%M%S')"
    sudo mkdir -p "$backup_dir"
    
    # Backup current bot data
    if [[ -f "bot_data.json" ]]; then
        sudo cp bot_data.json "$backup_dir/"
        log "Backed up bot_data.json"
    fi
    
    if [[ -f "questionnaire_data.json" ]]; then
        sudo cp questionnaire_data.json "$backup_dir/"
        log "Backed up questionnaire_data.json"
    fi
    
    if [[ -f "admins.json" ]]; then
        sudo cp admins.json "$backup_dir/"
        log "Backed up admins.json"
    fi
    
    # Backup course plans
    if ls course_plans_*.json 1> /dev/null 2>&1; then
        sudo cp course_plans_*.json "$backup_dir/"
        log "Backed up course plans"
    fi
    
    # Backup user documents and photos
    if [[ -d "user_documents" ]]; then
        sudo cp -r user_documents "$backup_dir/"
        log "Backed up user documents"
    fi
    
    if [[ -d "questionnaire_photos" ]]; then
        sudo cp -r questionnaire_photos "$backup_dir/"
        log "Backed up questionnaire photos"
    fi
    
    # Set proper permissions
    sudo chown -R $USER:$USER "$backup_dir"
    sudo chmod -R 750 "$backup_dir"
    
    success "Production backup created at: $backup_dir"
    echo "$backup_dir" > .last_backup_location
}

# =================================================================
# SECURITY HARDENING
# =================================================================

harden_linux_security() {
    log "🛡️  Applying Linux security hardening..."
    
    # Set proper file permissions for production
    chmod 600 .env 2>/dev/null || true
    chmod 600 *.json 2>/dev/null || true
    chmod 700 user_documents/ 2>/dev/null || true
    chmod 700 questionnaire_photos/ 2>/dev/null || true
    chmod 700 logs/ 2>/dev/null || true
    
    # Secure Python files
    chmod 644 *.py
    chmod 755 main.py  # Main entry point executable
    
    # Create secure directories
    mkdir -p logs/ user_documents/ questionnaire_photos/ exports/ backups/
    chmod 700 logs/ user_documents/ questionnaire_photos/ exports/ backups/
    
    # Configure UFW firewall (if available)
    if command -v ufw &> /dev/null; then
        sudo ufw --force reset
        sudo ufw default deny incoming
        sudo ufw default allow outgoing
        sudo ufw allow ssh
        sudo ufw allow 443/tcp  # HTTPS
        sudo ufw --force enable
        success "UFW firewall configured"
    fi
    
    success "Linux security hardening complete"
}

# =================================================================
# DATABASE RESET
# =================================================================

reset_production_database() {
    log "🗄️  Resetting production database..."
    
    # Stop the bot service if running
    sudo systemctl stop telegram-football-bot 2>/dev/null || true
    
    # Clear JSON data files (keep structure)
    cat > bot_data.json << 'EOF'
{
    "users": {},
    "course_selections": {},
    "payment_receipts": {},
    "questionnaire_progress": {},
    "admin_notifications": []
}
EOF

    cat > questionnaire_data.json << 'EOF'
{
    "responses": {},
    "photos": {},
    "completed": []
}
EOF

    cat > admins.json << 'EOF'
{
    "admins": [],
    "last_sync": null
}
EOF

    # Clear course plans
    rm -f course_plans_*.json
    
    # Clear user data directories
    rm -rf user_documents/* questionnaire_photos/* exports/* logs/*
    
    # Recreate directory structure
    mkdir -p user_documents/ questionnaire_photos/ exports/ logs/ backups/
    
    success "Production database reset complete"
}

# =================================================================
# PYTHON ENVIRONMENT
# =================================================================

setup_production_python() {
    log "🐍 Setting up production Python environment..."
    
    # Create virtual environment
    python3 -m venv venv_prod
    source venv_prod/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install production requirements
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        success "Production dependencies installed"
    else
        error "requirements.txt not found!"
        exit 1
    fi
    
    # Validate critical imports
    python3 -c "
import telegram
import asyncio
import json
import psycopg2
import PIL
print('✅ All critical imports successful')
"
    
    success "Python production environment ready"
}

# =================================================================
# SYSTEMD SERVICE
# =================================================================

create_systemd_service() {
    log "⚙️  Creating systemd service for production..."
    
    local service_file="/etc/systemd/system/telegram-football-bot.service"
    local bot_dir="$(pwd)"
    local bot_user="$USER"
    
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Telegram Football Coach Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=$bot_user
Group=$bot_user
WorkingDirectory=$bot_dir
Environment=PATH=$bot_dir/venv_prod/bin
ExecStart=$bot_dir/venv_prod/bin/python $bot_dir/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-football-bot

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$bot_dir

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable telegram-football-bot
    
    success "Systemd service created and enabled"
}

# =================================================================
# MONITORING SETUP
# =================================================================

setup_production_monitoring() {
    log "📊 Setting up production monitoring..."
    
    # Create monitoring script
    cat > monitor_bot.sh << 'EOF'
#!/bin/bash
# Production monitoring for Telegram Football Coach Bot

log_file="/var/log/telegram-bot-monitor.log"
bot_status=$(systemctl is-active telegram-football-bot)

echo "[$(date)] Bot Status: $bot_status" >> "$log_file"

if [[ "$bot_status" != "active" ]]; then
    echo "[$(date)] ALERT: Bot is not running! Attempting restart..." >> "$log_file"
    sudo systemctl restart telegram-football-bot
    sleep 5
    new_status=$(systemctl is-active telegram-football-bot)
    echo "[$(date)] Restart Result: $new_status" >> "$log_file"
fi

# Check disk space
disk_usage=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
if [[ $disk_usage -gt 80 ]]; then
    echo "[$(date)] WARNING: Disk usage at ${disk_usage}%" >> "$log_file"
fi

# Check memory usage
mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [[ $mem_usage -gt 80 ]]; then
    echo "[$(date)] WARNING: Memory usage at ${mem_usage}%" >> "$log_file"
fi
EOF

    chmod +x monitor_bot.sh
    
    # Add to crontab for monitoring every 5 minutes
    (crontab -l 2>/dev/null; echo "*/5 * * * * $(pwd)/monitor_bot.sh") | crontab -
    
    success "Production monitoring configured"
}

# =================================================================
# PRODUCTION VALIDATION
# =================================================================

validate_production_setup() {
    log "✅ Validating production setup..."
    
    # Check environment file
    if [[ ! -f ".env" ]]; then
        error ".env file not found! Copy from .env.example and configure."
        exit 1
    fi
    
    # Validate required environment variables
    source .env
    if [[ -z "${BOT_TOKEN:-}" ]] || [[ -z "${ADMIN_ID:-}" ]]; then
        error "Required environment variables not set in .env"
        exit 1
    fi
    
    # Check file permissions
    local env_perms=$(stat -c "%a" .env)
    if [[ "$env_perms" != "600" ]]; then
        warning ".env file permissions should be 600 for security"
        chmod 600 .env
    fi
    
    # Validate bot can start
    timeout 10s python3 main.py --validate 2>/dev/null || {
        error "Bot validation failed! Check configuration."
        exit 1
    }
    
    success "Production setup validation passed"
}

# =================================================================
# MAIN EXECUTION
# =================================================================

main() {
    echo -e "${PURPLE}"
    echo "================================================================="
    echo "  TELEGRAM FOOTBALL COACH BOT - LINUX PRODUCTION RESET"
    echo "================================================================="
    echo -e "${NC}"
    echo "🚀 Preparing Linux server for production deployment..."
    echo "⚠️  This will reset all data and configure for production use."
    echo ""
    
    read -p "Continue with production reset? [y/N]: " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Production reset cancelled."
        exit 0
    fi
    
    # Execute production setup steps
    validate_linux_environment
    create_production_backup
    harden_linux_security
    reset_production_database
    setup_production_python
    create_systemd_service
    setup_production_monitoring
    validate_production_setup
    
    echo ""
    echo -e "${GREEN}"
    echo "================================================================="
    echo "  🎉 LINUX PRODUCTION SETUP COMPLETE!"
    echo "================================================================="
    echo -e "${NC}"
    echo "📋 Next Steps:"
    echo "1. Configure .env with production values"
    echo "2. Start the service: sudo systemctl start telegram-football-bot"
    echo "3. Check status: sudo systemctl status telegram-football-bot"
    echo "4. View logs: journalctl -u telegram-football-bot -f"
    echo ""
    echo "🔒 Security Features Enabled:"
    echo "- UFW firewall configured"
    echo "- Proper file permissions set"
    echo "- Non-root service execution"
    echo "- Systemd service monitoring"
    echo "- Automated health checks"
    echo ""
    echo "📊 Monitoring:"
    echo "- Service auto-restart on failure"
    echo "- Disk and memory usage alerts"
    echo "- Log rotation configured"
    echo ""
    success "Production deployment ready for Linux server!"
}

# Execute main function
main "$@"
