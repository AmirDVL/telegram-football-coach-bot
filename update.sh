#!/bin/bash

# 🔄 Football Coach Bot - Update Script
# Updates the system and bot dependencies

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BOT_SERVICE="football-bot"
BOT_DIR="/opt/football-bot"
BOT_USER="footballbot"

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

# Function to update system packages
update_system() {
    print_status "Updating system packages..."
    apt update && apt upgrade -y
    print_success "System packages updated"
}

# Function to update Python packages
update_python_packages() {
    print_status "Updating Python packages..."
    sudo -u $BOT_USER bash -c "cd $BOT_DIR && source venv/bin/activate && pip install --upgrade pip"
    sudo -u $BOT_USER bash -c "cd $BOT_DIR && source venv/bin/activate && pip install --upgrade -r requirements.txt"
    print_success "Python packages updated"
}

# Function to restart bot service
restart_bot() {
    print_status "Restarting bot service..."
    systemctl restart $BOT_SERVICE
    sleep 3
    
    if systemctl is-active --quiet $BOT_SERVICE; then
        print_success "Bot restarted successfully"
    else
        print_error "Failed to restart bot"
        print_status "Checking logs..."
        journalctl -u $BOT_SERVICE -n 20 --no-pager
        exit 1
    fi
}

# Function to clean up old files
cleanup() {
    print_status "Cleaning up old files..."
    
    # Clean pip cache
    sudo -u $BOT_USER bash -c "cd $BOT_DIR && source venv/bin/activate && pip cache purge"
    
    # Clean old log files
    find /var/log -name "*.log.*" -mtime +30 -delete 2>/dev/null || true
    
    # Clean package cache
    apt autoremove -y
    apt autoclean
    
    print_success "Cleanup completed"
}

# Main update function
main() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        print_status "Please run: sudo bash update.sh"
        exit 1
    fi
    
    print_status "🔄 Starting update process..."
    
    # Create backup before updating
    if [[ -f "$BOT_DIR/backup.sh" ]]; then
        print_status "Creating backup before update..."
        sudo -u $BOT_USER $BOT_DIR/backup.sh
    fi
    
    update_system
    update_python_packages
    restart_bot
    cleanup
    
    print_success "🎉 Update completed successfully!"
    print_status "Bot status:"
    systemctl status $BOT_SERVICE --no-pager -l
}

# Run main function
main "$@"
