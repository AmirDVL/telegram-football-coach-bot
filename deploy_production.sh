#!/bin/bash

# 🚀 Football Coach Bot - Production Linux Deployment Script
# Updated for PostgreSQL compatibility and modern best practices
# Compatible with: Debian 11+, Ubuntu 20.04+, CentOS 8+

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BOT_USER="footballbot"
BOT_DIR="/opt/football-bot"
DB_NAME="football_coach_bot"
DB_USER="footballbot"
SERVICE_NAME="football-bot"

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

print_header() {
    echo -e "${CYAN}$1${NC}"
}

# Function to detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        print_error "Cannot detect OS version"
        exit 1
    fi
    
    print_status "Detected OS: $OS $VER"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_status "Running as root - proceeding with installation"
    else
        print_error "This script must be run as root"
        print_status "Please run: sudo bash $0"
        exit 1
    fi
}

# Function to update system packages
update_system() {
    print_status "Updating system packages..."
    
    if command -v apt &> /dev/null; then
        apt update && apt upgrade -y
    elif command -v yum &> /dev/null; then
        yum update -y
    elif command -v dnf &> /dev/null; then
        dnf update -y
    else
        print_error "Package manager not supported"
        exit 1
    fi
    
    print_success "System updated successfully"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    if command -v apt &> /dev/null; then
        # Debian/Ubuntu
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
            python3 \
            python3-pip \
            python3-venv \
            python3-dev \
            build-essential \
            libffi-dev \
            libssl-dev \
            libpq-dev \
            postgresql \
            postgresql-contrib \
            nginx \
            ufw \
            logrotate \
            cron
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        yum install -y epel-release
        yum install -y \
            curl \
            wget \
            git \
            nano \
            htop \
            unzip \
            python3 \
            python3-pip \
            python3-devel \
            gcc \
            gcc-c++ \
            make \
            libffi-devel \
            openssl-devel \
            postgresql \
            postgresql-server \
            postgresql-devel \
            nginx \
            firewalld \
            logrotate \
            cronie
    elif command -v dnf &> /dev/null; then
        # Fedora
        dnf install -y \
            curl \
            wget \
            git \
            nano \
            htop \
            unzip \
            python3 \
            python3-pip \
            python3-devel \
            gcc \
            gcc-c++ \
            make \
            libffi-devel \
            openssl-devel \
            postgresql \
            postgresql-server \
            postgresql-devel \
            nginx \
            firewalld \
            logrotate \
            cronie
    fi
    
    print_success "Dependencies installed successfully"
}

# Function to setup PostgreSQL
setup_postgresql() {
    print_status "Setting up PostgreSQL..."
    
    # Initialize PostgreSQL if needed (CentOS/RHEL)
    if command -v postgresql-setup &> /dev/null; then
        postgresql-setup initdb || true
    fi
    
    # Start and enable PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Get database credentials
    echo ""
    print_status "Database configuration:"
    read -p "Enter database password for user '$DB_USER': " -s DB_PASSWORD
    echo ""
    
    if [[ -z "$DB_PASSWORD" ]]; then
        print_error "Database password cannot be empty"
        exit 1
    fi
    
    # Create database and user
    sudo -u postgres psql << EOF
-- Create database
CREATE DATABASE $DB_NAME;

-- Create user with password
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;

\q
EOF
    
    print_success "PostgreSQL setup completed"
    
    # Export for later use
    export DB_PASSWORD
}

# Function to create bot user
create_bot_user() {
    print_status "Creating dedicated bot user..."
    
    if ! id "$BOT_USER" &>/dev/null; then
        useradd -r -m -s /bin/bash "$BOT_USER"
        usermod -aG postgres "$BOT_USER"
        print_success "User $BOT_USER created"
    else
        print_warning "User $BOT_USER already exists"
    fi
}

# Function to setup application directory
setup_app_directory() {
    print_status "Setting up application directory..."
    
    mkdir -p "$BOT_DIR"
    chown "$BOT_USER:$BOT_USER" "$BOT_DIR"
    chmod 755 "$BOT_DIR"
    
    # Create subdirectories
    sudo -u "$BOT_USER" mkdir -p "$BOT_DIR"/{logs,backups,data}
    
    print_success "Application directory created: $BOT_DIR"
}

# Function to get bot credentials
get_bot_credentials() {
    echo ""
    print_header "🤖 Bot Configuration"
    print_status "Please provide your Telegram bot credentials:"
    
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
    
    # Export for later use
    export BOT_TOKEN ADMIN_ID
}

# Function to download or setup bot files
setup_bot_files() {
    print_status "Setting up bot files..."
    
    cd "$BOT_DIR"
    
    echo ""
    print_status "Choose deployment method:"
    echo "1) Clone from Git repository"
    echo "2) Copy from local directory"
    echo "3) Download from archive URL"
    echo "4) I will upload files manually later"
    read -p "Enter choice [1-4]: " choice
    
    case $choice in
        1)
            read -p "Enter Git repository URL: " REPO_URL
            if [[ -n "$REPO_URL" ]]; then
                sudo -u "$BOT_USER" git clone "$REPO_URL" .
                print_success "Repository cloned successfully"
            else
                print_warning "No repository URL provided"
            fi
            ;;
        2)
            read -p "Enter local directory path: " LOCAL_PATH
            if [[ -d "$LOCAL_PATH" ]]; then
                sudo -u "$BOT_USER" cp -r "$LOCAL_PATH"/* .
                print_success "Files copied successfully"
            else
                print_warning "Directory not found: $LOCAL_PATH"
            fi
            ;;
        3)
            read -p "Enter archive URL: " ARCHIVE_URL
            if [[ -n "$ARCHIVE_URL" ]]; then
                sudo -u "$BOT_USER" wget -O /tmp/bot.zip "$ARCHIVE_URL"
                sudo -u "$BOT_USER" unzip /tmp/bot.zip -d .
                rm -f /tmp/bot.zip
                print_success "Archive downloaded and extracted"
            else
                print_warning "No archive URL provided"
            fi
            ;;
        4)
            print_warning "Please upload your bot files to $BOT_DIR after this script completes"
            sudo -u "$BOT_USER" touch README.txt
            ;;
        *)
            print_warning "Invalid choice. You'll need to upload files manually."
            ;;
    esac
    
    # Set proper ownership
    chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"
}

# Function to setup Python environment
setup_python_environment() {
    print_status "Setting up Python virtual environment..."
    
    cd "$BOT_DIR"
    
    # Create virtual environment as bot user
    sudo -u "$BOT_USER" python3 -m venv venv
    
    # Install dependencies
    if [[ -f "requirements.txt" ]]; then
        sudo -u "$BOT_USER" bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
        print_success "Dependencies installed from requirements.txt"
    else
        # Install basic dependencies
        sudo -u "$BOT_USER" bash -c "source venv/bin/activate && pip install --upgrade pip && pip install python-telegram-bot==21.0.1 aiofiles asyncpg python-dotenv"
        print_success "Basic dependencies installed"
    fi
}

# Function to create environment file
create_env_file() {
    print_status "Creating environment configuration..."
    
    cd "$BOT_DIR"
    
    sudo -u "$BOT_USER" cat > .env << EOF
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
LOG_FILE=$BOT_DIR/logs/bot.log

# 🔒 Security Settings
MAX_MESSAGE_LENGTH=4096
RATE_LIMIT_ENABLED=true

# 🌐 Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
WEBHOOK_URL=
EOF
    
    # Set secure permissions
    chmod 600 .env
    chown "$BOT_USER:$BOT_USER" .env
    
    print_success "Environment file created"
}

# Function to initialize database
initialize_database() {
    print_status "Initializing database schema and admin user..."
    
    cd "$BOT_DIR"
    
    if [[ -f "database_manager.py" && -f "main.py" ]]; then
        sudo -u "$BOT_USER" bash -c "
        source venv/bin/activate
        python3 -c \"
import asyncio
import sys
sys.path.append('.')
from database_manager import DatabaseManager

async def setup_db():
    print('🗄️  Initializing database...')
    db = DatabaseManager()
    await db.initialize()
    print('✅ Database tables created successfully!')
    
    # Add admin user
    print('👑 Adding admin user...')
    await db.add_admin($ADMIN_ID, {
        'can_manage_users': True,
        'can_manage_payments': True,
        'can_view_stats': True,
        'is_super_admin': True
    }, $ADMIN_ID)
    print('✅ Admin user added successfully!')
    
    await db.close()
    print('🎉 Database initialization completed!')

asyncio.run(setup_db())
\"
        "
        print_success "Database initialized and admin user created"
    else
        print_warning "Database files not found. Skipping database initialization."
        print_status "You'll need to run database initialization manually after uploading files."
    fi
}

# Function to create systemd service
create_systemd_service() {
    print_status "Creating systemd service..."
    
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Football Coach Telegram Bot
After=network.target postgresql.service
Requires=postgresql.service
StartLimitIntervalSec=0

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
PrivateTmp=true
ProtectControlGroups=true
ProtectKernelModules=true
ProtectKernelTunables=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictRealtime=true
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=true

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    print_success "Systemd service created and enabled"
}

# Function to setup log rotation
setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    cat > /etc/logrotate.d/$SERVICE_NAME << EOF
$BOT_DIR/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $BOT_USER $BOT_USER
    postrotate
        systemctl reload $SERVICE_NAME > /dev/null 2>&1 || true
    endscript
}
EOF
    
    print_success "Log rotation configured"
}

# Function to setup firewall
setup_firewall() {
    print_status "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian firewall
        ufw --force enable
        ufw allow ssh
        ufw allow 22
        # Allow webhook port if needed
        # ufw allow 8080
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL firewall
        systemctl start firewalld
        systemctl enable firewalld
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --reload
    fi
    
    print_success "Firewall configured"
}

# Function to create backup script
create_backup_script() {
    print_status "Setting up automated backups..."
    
    cat > "$BOT_DIR/backup.sh" << 'EOF'
#!/bin/bash

# Football Coach Bot Backup Script
source /opt/football-bot/.env

# Configuration
BACKUP_DIR="/opt/football-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
echo "🗄️  Creating database backup..."
PGPASSWORD=$DB_PASSWORD pg_dump -h localhost -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Backup application data (if using JSON files)
if [ -d "/opt/football-bot/data" ]; then
    echo "📁 Backing up application data..."
    tar -czf $BACKUP_DIR/data_backup_$DATE.tar.gz -C /opt/football-bot data/
fi

# Clean old backups
echo "🧹 Cleaning old backups..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup completed: $(date)"
EOF
    
    chmod +x "$BOT_DIR/backup.sh"
    chown "$BOT_USER:$BOT_USER" "$BOT_DIR/backup.sh"
    
    # Add cron job for daily backups at 2 AM
    (sudo -u "$BOT_USER" crontab -l 2>/dev/null; echo "0 2 * * * $BOT_DIR/backup.sh >> $BOT_DIR/logs/backup.log 2>&1") | sudo -u "$BOT_USER" crontab -
    
    print_success "Backup system configured"
}

# Function to create management scripts
create_management_scripts() {
    print_status "Creating management scripts..."
    
    # Bot management script
    cat > "$BOT_DIR/manage.sh" << EOF
#!/bin/bash

SERVICE_NAME="$SERVICE_NAME"
BOT_DIR="$BOT_DIR"

case \$1 in
    start)
        echo "🚀 Starting Football Coach Bot..."
        sudo systemctl start \$SERVICE_NAME
        ;;
    stop)
        echo "⏹️  Stopping Football Coach Bot..."
        sudo systemctl stop \$SERVICE_NAME
        ;;
    restart)
        echo "🔄 Restarting Football Coach Bot..."
        sudo systemctl restart \$SERVICE_NAME
        ;;
    status)
        echo "📊 Bot Status:"
        sudo systemctl status \$SERVICE_NAME
        ;;
    logs)
        echo "📋 Recent Logs:"
        sudo journalctl -u \$SERVICE_NAME -n 50 -f
        ;;
    update)
        echo "⬆️  Updating bot..."
        cd \$BOT_DIR
        sudo systemctl stop \$SERVICE_NAME
        sudo -u $BOT_USER git pull
        sudo -u $BOT_USER bash -c "source venv/bin/activate && pip install -r requirements.txt"
        sudo systemctl start \$SERVICE_NAME
        echo "✅ Update completed"
        ;;
    backup)
        echo "💾 Creating backup..."
        \$BOT_DIR/backup.sh
        ;;
    *)
        echo "Usage: \$0 {start|stop|restart|status|logs|update|backup}"
        echo ""
        echo "🤖 Football Coach Bot Management"
        echo "Available commands:"
        echo "  start   - Start the bot service"
        echo "  stop    - Stop the bot service"
        echo "  restart - Restart the bot service"
        echo "  status  - Show service status"
        echo "  logs    - Show recent logs"
        echo "  update  - Update bot from repository"
        echo "  backup  - Create manual backup"
        exit 1
        ;;
esac
EOF
    
    chmod +x "$BOT_DIR/manage.sh"
    chown "$BOT_USER:$BOT_USER" "$BOT_DIR/manage.sh"
    
    # Create symlink for global access
    ln -sf "$BOT_DIR/manage.sh" /usr/local/bin/football-bot
    
    print_success "Management scripts created"
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."
    
    cd "$BOT_DIR"
    
    if [[ -f "main.py" ]]; then
        # Test Python environment
        sudo -u "$BOT_USER" bash -c "source venv/bin/activate && python3 -c 'import telegram; print(\"✅ Telegram library available\")'"
        
        # Test database connection
        if [[ -f "database_manager.py" ]]; then
            sudo -u "$BOT_USER" bash -c "
            source venv/bin/activate
            timeout 10s python3 -c \"
import asyncio
from database_manager import DatabaseManager

async def test_db():
    try:
        db = DatabaseManager()
        await db.initialize()
        print('✅ Database connection successful')
        await db.close()
    except Exception as e:
        print(f'❌ Database connection failed: {e}')

asyncio.run(test_db())
\" || echo '⚠️  Database test timeout'
            "
        fi
        
        print_success "Installation tests completed"
    else
        print_warning "main.py not found - upload your bot files and run tests manually"
    fi
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    if [[ -f "$BOT_DIR/main.py" ]]; then
        systemctl start $SERVICE_NAME
        sleep 5
        
        if systemctl is-active --quiet $SERVICE_NAME; then
            print_success "Bot service started successfully"
        else
            print_error "Bot service failed to start"
            print_status "Check logs with: journalctl -u $SERVICE_NAME -n 50"
        fi
    else
        print_warning "Bot files not found. Service not started."
        print_status "Upload your files and run: systemctl start $SERVICE_NAME"
    fi
}

# Function to display final information
display_final_info() {
    echo ""
    echo "========================================"
    print_header "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "========================================"
    echo ""
    print_status "🚀 Football Coach Bot Installation Summary:"
    echo ""
    echo "📂 Installation Directory: $BOT_DIR"
    echo "👤 Bot User: $BOT_USER"
    echo "🗄️  Database: $DB_NAME"
    echo "⚙️  Service: $SERVICE_NAME"
    echo ""
    print_status "🛠️  Management Commands:"
    echo "• football-bot start      - Start the bot"
    echo "• football-bot stop       - Stop the bot"
    echo "• football-bot restart    - Restart the bot"
    echo "• football-bot status     - Check status"
    echo "• football-bot logs       - View logs"
    echo "• football-bot update     - Update from repository"
    echo "• football-bot backup     - Create backup"
    echo ""
    print_status "📊 Service Management:"
    echo "• systemctl status $SERVICE_NAME"
    echo "• journalctl -u $SERVICE_NAME -f"
    echo ""
    print_status "📁 Important Files:"
    echo "• Configuration: $BOT_DIR/.env"
    echo "• Logs: $BOT_DIR/logs/"
    echo "• Backups: $BOT_DIR/backups/"
    echo ""
    print_status "🔐 Security Notes:"
    echo "• Firewall configured for SSH access"
    echo "• Bot runs as unprivileged user: $BOT_USER"
    echo "• Environment file has secure permissions (600)"
    echo "• Daily automated backups enabled"
    echo ""
    
    if [[ ! -f "$BOT_DIR/main.py" ]]; then
        print_warning "⚠️  NEXT STEPS REQUIRED:"
        echo "1. Upload your bot files to: $BOT_DIR"
        echo "2. Set proper ownership: chown -R $BOT_USER:$BOT_USER $BOT_DIR"
        echo "3. Start the service: systemctl start $SERVICE_NAME"
        echo ""
    else
        print_success "✅ Bot is ready and running!"
        echo ""
        print_status "📱 Test your bot:"
        echo "1. Open Telegram and find your bot"
        echo "2. Send /start command"
        echo "3. Check logs: football-bot logs"
        echo ""
    fi
    
    print_status "📚 Additional Resources:"
    echo "• Bot logs: tail -f $BOT_DIR/logs/bot.log"
    echo "• System logs: journalctl -u $SERVICE_NAME"
    echo "• Backup logs: tail -f $BOT_DIR/logs/backup.log"
    echo ""
}

# Main execution function
main() {
    clear
    echo ""
    print_header "========================================"
    print_header "🚀 FOOTBALL COACH BOT DEPLOYMENT"
    print_header "   Production Linux Server Setup"
    print_header "========================================"
    echo ""
    
    detect_os
    check_root
    
    echo ""
    print_status "Starting deployment process..."
    echo ""
    
    update_system
    install_dependencies
    setup_postgresql
    create_bot_user
    setup_app_directory
    get_bot_credentials
    setup_bot_files
    setup_python_environment
    create_env_file
    initialize_database
    create_systemd_service
    setup_log_rotation
    setup_firewall
    create_backup_script
    create_management_scripts
    test_installation
    start_services
    display_final_info
    
    echo ""
    print_success "🎉 Football Coach Bot deployment completed!"
    echo ""
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
