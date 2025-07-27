#!/bin/bash

# 🚀 Football Coach Bot - Automated Debian Setup Script
# This script automates the deployment process for a fresh Debian/Ubuntu server

set -e  # Exit on any error

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

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for security reasons."
        print_status "Please run as a regular user with sudo privileges."
        exit 1
    fi
}

# Function to check if user has sudo privileges
check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        print_error "This script requires sudo privileges."
        print_status "Please ensure your user has sudo access."
        exit 1
    fi
}

# Function to update system
update_system() {
    print_status "Updating system packages..."
    sudo apt update && sudo apt upgrade -y
    print_success "System updated successfully"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    sudo apt install -y \
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
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        postgresql \
        postgresql-contrib
    
    print_success "Dependencies installed successfully"
}

# Function to setup PostgreSQL
setup_postgresql() {
    print_status "Setting up PostgreSQL..."
    
    # Start and enable PostgreSQL
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    # Get database credentials from user
    echo ""
    print_status "Setting up database credentials..."
    read -p "Enter database name [football_coach_bot]: " DB_NAME
    DB_NAME=${DB_NAME:-football_coach_bot}
    
    read -p "Enter database username [footballbot]: " DB_USER
    DB_USER=${DB_USER:-footballbot}
    
    read -s -p "Enter database password: " DB_PASSWORD
    echo ""
    
    if [[ -z "$DB_PASSWORD" ]]; then
        print_error "Database password cannot be empty"
        exit 1
    fi
    
    # Create database and user
    sudo -u postgres psql << EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
\q
EOF
    
    print_success "PostgreSQL setup completed"
    
    # Store credentials for later use
    export DB_NAME DB_USER DB_PASSWORD
}

# Function to setup application directory
setup_app_directory() {
    print_status "Setting up application directory..."
    
    sudo mkdir -p /opt/football-bot
    sudo chown $USER:$USER /opt/football-bot
    
    print_success "Application directory created"
}

# Function to get bot credentials
get_bot_credentials() {
    echo ""
    print_status "Please provide your Telegram bot credentials..."
    
    read -p "Enter your Bot Token (from @BotFather): " BOT_TOKEN
    if [[ -z "$BOT_TOKEN" ]]; then
        print_error "Bot token cannot be empty"
        exit 1
    fi
    
    read -p "Enter your Telegram User ID (Admin ID): " ADMIN_ID
    if [[ -z "$ADMIN_ID" ]]; then
        print_error "Admin ID cannot be empty"
        exit 1
    fi
}

# Function to clone repository or setup files
setup_bot_files() {
    print_status "Setting up bot files..."
    
    cd /opt/football-bot
    
    echo ""
    print_status "Choose how to get the bot files:"
    echo "1) Clone from Git repository"
    echo "2) I will upload files manually later"
    read -p "Enter choice [1-2]: " choice
    
    case $choice in
        1)
            read -p "Enter Git repository URL: " REPO_URL
            if [[ -n "$REPO_URL" ]]; then
                git clone "$REPO_URL" .
                print_success "Repository cloned successfully"
            else
                print_warning "No repository URL provided. You'll need to upload files manually."
            fi
            ;;
        2)
            print_warning "Please upload your bot files to /opt/football-bot/ after this script completes"
            ;;
        *)
            print_warning "Invalid choice. You'll need to upload files manually."
            ;;
    esac
}

# Function to setup Python environment
setup_python_environment() {
    print_status "Setting up Python virtual environment..."
    
    cd /opt/football-bot
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies if requirements.txt exists
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        print_success "Dependencies installed from requirements.txt"
    else
        print_status "Installing basic dependencies..."
        pip install python-telegram-bot==21.0.1 aiofiles asyncpg python-dotenv
        print_success "Basic dependencies installed"
    fi
}

# Function to create environment file
create_env_file() {
    print_status "Creating environment configuration..."
    
    cd /opt/football-bot
    
    cat > .env << EOF
# 🤖 Telegram Bot Configuration
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID

# 🗄️ Database Configuration (PostgreSQL)
USE_DATABASE=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# 🛡️ Production Settings
DEBUG=false

# 📊 Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/opt/football-bot/logs/bot.log

# 🔒 Security Settings
MAX_MESSAGE_LENGTH=4096
RATE_LIMIT_ENABLED=true
EOF
    
    # Set secure permissions
    chmod 600 .env
    chown $USER:$USER .env
    
    # Create logs directory
    mkdir -p logs
    
    print_success "Environment file created with production settings"
}

# Function to initialize database
initialize_database() {
    print_status "Initializing database schema..."
    
    cd /opt/football-bot
    source venv/bin/activate
    
    # Check if database_manager.py exists
    if [[ -f "database_manager.py" ]]; then
        python3 -c "
import asyncio
from database_manager import DatabaseManager

async def setup_db():
    print('Initializing database...')
    db = DatabaseManager()
    await db.initialize()
    print('Database initialized successfully!')
    
    # Add initial admin user
    print('Adding admin user...')
    await db.add_admin($ADMIN_ID, {
        'can_manage_users': True,
        'can_manage_payments': True,
        'can_view_stats': True,
        'is_super_admin': True
    }, $ADMIN_ID)
    print('Admin user added successfully!')
    
    await db.close()

asyncio.run(setup_db())
"
        print_success "Database initialized and admin user added successfully"
    else
        print_warning "database_manager.py not found. Database initialization skipped."
    fi
}

# Function to create systemd service
create_systemd_service() {
    print_status "Creating systemd service..."
    
    sudo tee /etc/systemd/system/football-bot.service > /dev/null << EOF
[Unit]
Description=Football Coach Telegram Bot
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/football-bot
Environment=PATH=/opt/football-bot/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/football-bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/football-bot

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable football-bot
    
    print_success "Systemd service created and enabled"
}

# Function to setup firewall
setup_firewall() {
    print_status "Setting up firewall..."
    
    sudo ufw --force enable
    sudo ufw allow ssh
    sudo ufw allow 22
    
    print_success "Firewall configured"
}

# Function to create backup script
create_backup_script() {
    print_status "Setting up automated backups..."
    
    cat > /opt/football-bot/backup.sh << EOF
#!/bin/bash

# Configuration
DB_NAME="$DB_NAME"
DB_USER="$DB_USER"
BACKUP_DIR="/opt/football-bot/backups"
DATE=\$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p \$BACKUP_DIR

# Create database backup
pg_dump -h localhost -U \$DB_USER \$DB_NAME > \$BACKUP_DIR/db_backup_\$DATE.sql

# Compress the backup
gzip \$BACKUP_DIR/db_backup_\$DATE.sql

# Keep only last 7 days of backups
find \$BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_backup_\$DATE.sql.gz"
EOF
    
    chmod +x /opt/football-bot/backup.sh
    mkdir -p /opt/football-bot/backups
    
    # Add cron job for daily backups
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/football-bot/backup.sh >> /opt/football-bot/backup.log 2>&1") | crontab -
    
    print_success "Backup system configured"
}

# Function to test bot
test_bot() {
    print_status "Testing bot configuration..."
    
    cd /opt/football-bot
    
    if [[ -f "main.py" ]]; then
        source venv/bin/activate
        timeout 10s python3 main.py || true
        print_success "Bot test completed (check if no errors appeared above)"
    else
        print_warning "main.py not found. Bot test skipped."
    fi
}

# Function to start bot service
start_bot_service() {
    print_status "Starting bot service..."
    
    if [[ -f "/opt/football-bot/main.py" ]]; then
        sudo systemctl start football-bot
        sleep 5
        
        if sudo systemctl is-active --quiet football-bot; then
            print_success "Bot service started successfully"
        else
            print_error "Bot service failed to start"
            print_status "Check logs with: sudo journalctl -u football-bot -n 50"
        fi
    else
        print_warning "main.py not found. Service not started."
        print_status "Upload your bot files and run: sudo systemctl start football-bot"
    fi
}

# Function to display final information
display_final_info() {
    echo ""
    echo "========================================"
    print_success "🎉 Setup completed successfully!"
    echo "========================================"
    echo ""
    print_status "Important information:"
    echo "• Application directory: /opt/football-bot"
    echo "• Database: $DB_NAME"
    echo "• Service name: football-bot"
    echo ""
    print_status "Useful commands:"
    echo "• Check service status: sudo systemctl status football-bot"
    echo "• View logs: sudo journalctl -u football-bot -f"
    echo "• Restart service: sudo systemctl restart football-bot"
    echo "• Stop service: sudo systemctl stop football-bot"
    echo ""
    print_status "Next steps:"
    if [[ ! -f "/opt/football-bot/main.py" ]]; then
        echo "1. Upload your bot files to /opt/football-bot/"
        echo "2. Start the service: sudo systemctl start football-bot"
    else
        echo "1. Test your bot by sending /start on Telegram"
        echo "2. Monitor logs for any issues"
    fi
    echo "3. Set up SSL certificate if needed (for webhook mode)"
    echo ""
    print_warning "Remember to:"
    echo "• Keep your .env file secure (contains sensitive credentials)"
    echo "• Regularly update your system and bot"
    echo "• Monitor disk space and logs"
    echo ""
}

# Main execution
main() {
    echo "========================================"
    echo "🚀 Football Coach Bot Setup Script"
    echo "========================================"
    echo ""
    
    check_root
    check_sudo
    
    update_system
    install_dependencies
    setup_postgresql
    setup_app_directory
    get_bot_credentials
    setup_bot_files
    setup_python_environment
    create_env_file
    initialize_database
    create_systemd_service
    setup_firewall
    create_backup_script
    test_bot
    start_bot_service
    display_final_info
}

# Run main function
main "$@"
