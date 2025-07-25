#!/bin/bash

# 🚀 Football Coach Bot - Complete Debian Server Deployment Script
# This script sets up everything from scratch on a fresh Debian/Ubuntu server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BOT_USER="footballbot"
BOT_DIR="/opt/football-bot"
DB_NAME="football_coach_bot"
DB_USER="footballbot"

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

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_status "Running as root - this is correct for initial setup"
    else
        print_error "This script must be run as root for initial setup"
        print_status "Please run: sudo bash deploy.sh"
        exit 1
    fi
}

# Function to update system packages
update_system() {
    print_status "Updating system packages..."
    apt update && apt upgrade -y
    print_success "System updated successfully"
}

# Function to install essential tools
install_essential_tools() {
    print_status "Installing essential tools..."
    apt install -y \
        curl \
        wget \
        git \
        nano \
        htop \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        build-essential
    print_success "Essential tools installed"
}

# Function to install Python
install_python() {
    print_status "Installing Python 3 and dependencies..."
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        libffi-dev \
        libssl-dev \
        libpq-dev
    
    # Upgrade pip
    python3 -m pip install --upgrade pip
    print_success "Python installed successfully"
    
    # Show Python version
    python_version=$(python3 --version)
    print_status "Python version: $python_version"
}

# Function to install PostgreSQL
install_postgresql() {
    print_status "Installing PostgreSQL..."
    apt install -y postgresql postgresql-contrib
    
    # Start and enable PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    print_success "PostgreSQL installed and started"
    
    # Show PostgreSQL status
    systemctl status postgresql --no-pager -l
}

# Function to create bot user
create_bot_user() {
    print_status "Creating bot user: $BOT_USER"
    
    # Create user if doesn't exist
    if ! id "$BOT_USER" &>/dev/null; then
        adduser --system --group --home $BOT_DIR $BOT_USER
        print_success "User $BOT_USER created"
    else
        print_warning "User $BOT_USER already exists"
    fi
    
    # Create bot directory
    mkdir -p $BOT_DIR
    chown $BOT_USER:$BOT_USER $BOT_DIR
}

# Function to setup firewall
setup_firewall() {
    print_status "Setting up firewall..."
    
    # Install ufw if not installed
    apt install -y ufw
    
    # Reset firewall rules
    ufw --force reset
    
    # Allow SSH (important!)
    ufw allow ssh
    ufw allow 22
    
    # Enable firewall
    echo "y" | ufw enable
    
    print_success "Firewall configured"
    ufw status
}

# Function to setup database
setup_database() {
    print_status "Setting up PostgreSQL database..."
    
    # Generate secure password if not provided
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 32)
        print_status "Generated secure database password"
    fi
    
    # Create database and user
    sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
\q
EOF
    
    print_success "Database setup completed"
    print_status "Database: $DB_NAME"
    print_status "User: $DB_USER"
    print_warning "Password: $DB_PASSWORD"
    print_warning "SAVE THIS PASSWORD! You'll need it for the .env file"
    
    # Save password to file for later use
    echo "DB_PASSWORD=$DB_PASSWORD" > /tmp/db_credentials.txt
    chmod 600 /tmp/db_credentials.txt
}

# Function to test database connection
test_database() {
    print_status "Testing database connection..."
    
    if sudo -u postgres psql -d $DB_NAME -c "SELECT version();" &>/dev/null; then
        print_success "Database connection test passed"
    else
        print_error "Database connection test failed"
        exit 1
    fi
}

# Function to clone repository
clone_repository() {
    print_status "Repository setup..."
    
    if [ -n "$REPO_URL" ]; then
        print_status "Cloning repository from: $REPO_URL"
        sudo -u $BOT_USER git clone $REPO_URL $BOT_DIR
        print_success "Repository cloned successfully"
    else
        print_warning "No repository URL provided"
        print_status "You'll need to upload your bot files manually to: $BOT_DIR"
        print_status "Make sure to upload:"
        echo "  - main.py"
        echo "  - config.py"
        echo "  - data_manager.py"
        echo "  - database_manager.py"
        echo "  - questionnaire_manager.py"
        echo "  - admin_panel.py"
        echo "  - admin_manager.py"
        echo "  - requirements.txt"
        echo "  - .env.example"
    fi
}

# Function to setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    # Switch to bot user and setup venv
    sudo -u $BOT_USER bash <<EOF
cd $BOT_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
EOF
    
    print_success "Virtual environment created"
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Check if requirements.txt exists
    if [ -f "$BOT_DIR/requirements.txt" ]; then
        sudo -u $BOT_USER bash <<EOF
cd $BOT_DIR
source venv/bin/activate
pip install -r requirements.txt
EOF
        print_success "Dependencies installed from requirements.txt"
    else
        print_warning "requirements.txt not found, installing essential packages..."
        sudo -u $BOT_USER bash <<EOF
cd $BOT_DIR
source venv/bin/activate
pip install python-telegram-bot==21.0.1 aiofiles asyncpg python-dotenv
EOF
        print_success "Essential dependencies installed"
    fi
}

# Function to create environment file
create_env_file() {
    print_status "Creating environment configuration..."
    
    # Load database password
    if [ -f "/tmp/db_credentials.txt" ]; then
        source /tmp/db_credentials.txt
    fi
    
    # Create .env file
    sudo -u $BOT_USER tee $BOT_DIR/.env > /dev/null <<EOF
# Telegram Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_ID=YOUR_TELEGRAM_USER_ID

# Database Configuration
USE_DATABASE=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# Production Settings
DEBUG=false
EOF
    
    # Set secure permissions
    chmod 600 $BOT_DIR/.env
    chown $BOT_USER:$BOT_USER $BOT_DIR/.env
    
    print_success "Environment file created: $BOT_DIR/.env"
    print_warning "IMPORTANT: Edit $BOT_DIR/.env and add your BOT_TOKEN and ADMIN_ID"
}

# Function to initialize database schema
init_database_schema() {
    print_status "Initializing database schema..."
    
    # Check if database_manager.py exists
    if [ -f "$BOT_DIR/database_manager.py" ]; then
        sudo -u $BOT_USER bash <<EOF
cd $BOT_DIR
source venv/bin/activate
python3 -c "
import asyncio
import sys
sys.path.append('.')
try:
    from database_manager import DatabaseManager
    async def setup_db():
        print('Initializing database...')
        db = DatabaseManager()
        await db.initialize()
        print('Database initialized successfully!')
        await db.close()
    asyncio.run(setup_db())
except Exception as e:
    print(f'Database initialization failed: {e}')
    print('You may need to initialize the database manually later.')
"
EOF
        print_success "Database schema initialized"
    else
        print_warning "database_manager.py not found, skipping database initialization"
        print_status "You'll need to initialize the database manually later"
    fi
}

# Function to create systemd service
create_systemd_service() {
    print_status "Creating systemd service..."
    
    tee /etc/systemd/system/football-bot.service > /dev/null <<EOF
[Unit]
Description=Football Coach Telegram Bot
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$BOT_USER
Group=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment=PATH=$BOT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$BOT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$BOT_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    systemctl enable football-bot
    
    print_success "Systemd service created and enabled"
}

# Function to setup log rotation
setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    tee /etc/logrotate.d/football-bot > /dev/null <<EOF
/var/log/journal/football-bot.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $BOT_USER $BOT_USER
}
EOF
    
    print_success "Log rotation configured"
}

# Function to create backup script
create_backup_script() {
    print_status "Creating backup script..."
    
    tee $BOT_DIR/backup.sh > /dev/null <<'EOF'
#!/bin/bash

# Configuration
DB_NAME="football_coach_bot"
DB_USER="footballbot"
BACKUP_DIR="/opt/football-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Compress the backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_backup_$DATE.sql.gz"
EOF
    
    # Make script executable
    chmod +x $BOT_DIR/backup.sh
    chown $BOT_USER:$BOT_USER $BOT_DIR/backup.sh
    
    # Create backups directory
    sudo -u $BOT_USER mkdir -p $BOT_DIR/backups
    
    print_success "Backup script created: $BOT_DIR/backup.sh"
}

# Function to setup cron for backups
setup_backup_cron() {
    print_status "Setting up automated backups..."
    
    # Add cron job for daily backups at 2 AM
    (sudo -u $BOT_USER crontab -l 2>/dev/null; echo "0 2 * * * $BOT_DIR/backup.sh >> $BOT_DIR/backup.log 2>&1") | sudo -u $BOT_USER crontab -
    
    print_success "Daily backup cron job scheduled for 2 AM"
}

# Function to create monitoring script
create_monitoring_script() {
    print_status "Creating monitoring script..."
    
    tee $BOT_DIR/monitor.sh > /dev/null <<'EOF'
#!/bin/bash

# Football Coach Bot Monitoring Script

echo "=== Football Coach Bot Status ==="
echo "Date: $(date)"
echo

# Service status
echo "Service Status:"
systemctl status football-bot --no-pager -l
echo

# Recent logs
echo "Recent Logs (last 20 lines):"
journalctl -u football-bot -n 20 --no-pager
echo

# System resources
echo "System Resources:"
echo "Memory Usage:"
free -h
echo
echo "Disk Usage:"
df -h /opt/football-bot
echo

# Database status
echo "Database Status:"
systemctl status postgresql --no-pager -l
echo

# Process information
echo "Bot Process:"
ps aux | grep -E "(python.*main.py|football-bot)" | grep -v grep
echo

# Network connectivity test
echo "Network Test (ping Telegram):"
ping -c 3 api.telegram.org 2>/dev/null | tail -3
EOF
    
    chmod +x $BOT_DIR/monitor.sh
    chown $BOT_USER:$BOT_USER $BOT_DIR/monitor.sh
    
    print_success "Monitoring script created: $BOT_DIR/monitor.sh"
}

# Function to test bot startup
test_bot_startup() {
    print_status "Testing bot startup..."
    
    # Check if main.py exists
    if [ ! -f "$BOT_DIR/main.py" ]; then
        print_warning "main.py not found, skipping startup test"
        return
    fi
    
    # Check if .env has bot token
    if grep -q "YOUR_BOT_TOKEN_HERE" $BOT_DIR/.env; then
        print_warning "Bot token not configured, skipping startup test"
        print_status "Please edit $BOT_DIR/.env with your BOT_TOKEN before starting"
        return
    fi
    
    print_status "Starting bot service..."
    systemctl start football-bot
    
    # Wait a moment for startup
    sleep 5
    
    # Check service status
    if systemctl is-active --quiet football-bot; then
        print_success "Bot service started successfully!"
        systemctl status football-bot --no-pager -l
    else
        print_error "Bot service failed to start"
        print_status "Check logs with: journalctl -u football-bot -f"
        systemctl status football-bot --no-pager -l
    fi
}

# Function to display final instructions
show_final_instructions() {
    print_success "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
    echo
    print_status "Next steps:"
    echo "1. Edit the environment file:"
    echo "   nano $BOT_DIR/.env"
    echo "   - Add your BOT_TOKEN from @BotFather"
    echo "   - Add your ADMIN_ID (your Telegram user ID)"
    echo
    echo "2. Start the bot:"
    echo "   systemctl start football-bot"
    echo
    echo "3. Check bot status:"
    echo "   systemctl status football-bot"
    echo
    echo "4. View live logs:"
    echo "   journalctl -u football-bot -f"
    echo
    echo "5. Monitor the bot:"
    echo "   $BOT_DIR/monitor.sh"
    echo
    print_status "Useful commands:"
    echo "- Start bot: systemctl start football-bot"
    echo "- Stop bot: systemctl stop football-bot"
    echo "- Restart bot: systemctl restart football-bot"
    echo "- View logs: journalctl -u football-bot -f"
    echo "- Run backup: $BOT_DIR/backup.sh"
    echo "- Monitor system: $BOT_DIR/monitor.sh"
    echo
    if [ -f "/tmp/db_credentials.txt" ]; then
        print_warning "Database credentials saved in: /tmp/db_credentials.txt"
        print_warning "Remember to delete this file after noting the password!"
    fi
    echo
    print_success "🎉 Your Football Coach Bot is ready for production!"
}

# Main execution function
main() {
    echo "🚀 Football Coach Bot - Debian Server Deployment"
    echo "================================================"
    echo
    
    # Check if repository URL provided
    if [ -n "$1" ]; then
        REPO_URL="$1"
        print_status "Repository URL: $REPO_URL"
    fi
    
    # Check if database password provided
    if [ -n "$2" ]; then
        DB_PASSWORD="$2"
        print_status "Using provided database password"
    fi
    
    print_status "Starting deployment process..."
    echo
    
    # Execute deployment steps
    check_root
    update_system
    install_essential_tools
    install_python
    install_postgresql
    create_bot_user
    setup_firewall
    setup_database
    test_database
    clone_repository
    setup_python_env
    install_python_deps
    create_env_file
    init_database_schema
    create_systemd_service
    setup_log_rotation
    create_backup_script
    setup_backup_cron
    create_monitoring_script
    test_bot_startup
    
    echo
    show_final_instructions
}

# Run main function with all arguments
main "$@"
