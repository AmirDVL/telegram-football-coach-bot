#!/bin/bash

# Football Coach Bot - Production Startup Script
# This script handles complete bot initialization and startup

set -e  # Exit on any error

# Configuration
BOT_DIR="/opt/football-bot"
BOT_USER="footballbot"
SERVICE_NAME="football-bot"
LOG_FILE="/opt/football-bot/startup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    echo -e "${RED}❌ ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

# Success message
success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

# Warning message
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# Info message
info() {
    echo -e "${BLUE}ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error_exit "Do not run this script as root. Run as the footballbot user or with sudo."
    fi
}

# Check system requirements
check_requirements() {
    info "Checking system requirements..."
    
    # Check if Python 3 is installed
    if ! command -v python3 &> /dev/null; then
        error_exit "Python 3 is not installed"
    fi
    
    # Check if PostgreSQL is running
    if ! systemctl is-active --quiet postgresql; then
        warning "PostgreSQL is not running. Starting PostgreSQL..."
        sudo systemctl start postgresql || error_exit "Failed to start PostgreSQL"
    fi
    
    # Check if bot directory exists
    if [[ ! -d "$BOT_DIR" ]]; then
        error_exit "Bot directory $BOT_DIR does not exist"
    fi
    
    # Check if virtual environment exists
    if [[ ! -d "$BOT_DIR/venv" ]]; then
        error_exit "Virtual environment not found at $BOT_DIR/venv"
    fi
    
    # Check if .env file exists
    if [[ ! -f "$BOT_DIR/.env" ]]; then
        error_exit "Environment file .env not found in $BOT_DIR"
    fi
    
    success "System requirements check passed"
}

# Validate environment variables
validate_environment() {
    info "Validating environment configuration..."
    
    cd "$BOT_DIR"
    source venv/bin/activate
    
    # Check critical environment variables
    if ! grep -q "BOT_TOKEN=" .env; then
        error_exit "BOT_TOKEN not found in .env file"
    fi
    
    if ! grep -q "ADMIN_ID=" .env; then
        error_exit "ADMIN_ID not found in .env file"
    fi
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    if [[ -z "$BOT_TOKEN" ]]; then
        error_exit "BOT_TOKEN is empty in .env file"
    fi
    
    if [[ -z "$ADMIN_ID" ]]; then
        error_exit "ADMIN_ID is empty in .env file"
    fi
    
    success "Environment validation passed"
}

# Test database connection
test_database() {
    info "Testing database connection..."
    
    cd "$BOT_DIR"
    source venv/bin/activate
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    # Test database connection with Python
    python3 -c "
import asyncio
import asyncpg
import os
import sys

async def test_db():
    try:
        if os.getenv('USE_DATABASE', 'false').lower() == 'true':
            conn = await asyncpg.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '5432')),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'football_coach_bot')
            )
            await conn.close()
            print('Database connection successful')
        else:
            print('Using JSON mode - database test skipped')
    except Exception as e:
        print(f'Database connection failed: {e}')
        sys.exit(1)

asyncio.run(test_db())
" || error_exit "Database connection test failed"
    
    success "Database connection test passed"
}

# Initialize database if needed
initialize_database() {
    info "Checking database initialization..."
    
    cd "$BOT_DIR"
    source venv/bin/activate
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    if [[ "$USE_DATABASE" == "true" ]]; then
        python3 -c "
import asyncio
import sys
import os
sys.path.append('.')

async def init_db():
    try:
        from database_manager import DatabaseManager
        db = DatabaseManager()
        await db.initialize()
        await db.close()
        print('Database initialized successfully')
    except Exception as e:
        print(f'Database initialization failed: {e}')
        sys.exit(1)

asyncio.run(init_db())
" || error_exit "Database initialization failed"
    else
        info "Using JSON mode - database initialization skipped"
    fi
    
    success "Database initialization completed"
}

# Test Telegram connectivity
test_telegram() {
    info "Testing Telegram API connectivity..."
    
    cd "$BOT_DIR"
    source venv/bin/activate
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    # Test Telegram connection
    python3 -c "
import asyncio
import sys
from telegram import Bot
from telegram.request import HTTPXRequest

async def test_telegram():
    try:
        request = HTTPXRequest(read_timeout=10, connect_timeout=10)
        bot = Bot(token='$BOT_TOKEN', request=request)
        me = await bot.get_me()
        print(f'Telegram connection successful: @{me.username}')
    except Exception as e:
        print(f'Telegram connection failed: {e}')
        sys.exit(1)

asyncio.run(test_telegram())
" || error_exit "Telegram API connectivity test failed"
    
    success "Telegram API connectivity test passed"
}

# Update bot dependencies
update_dependencies() {
    info "Updating bot dependencies..."
    
    cd "$BOT_DIR"
    source venv/bin/activate
    
    # Update pip
    pip install --upgrade pip
    
    # Install/update requirements
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
    else
        pip install python-telegram-bot python-dotenv aiofiles asyncpg pillow
    fi
    
    success "Dependencies updated successfully"
}

# Create or update systemd service
setup_systemd_service() {
    info "Setting up systemd service..."
    
    # Create systemd service file
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
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

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable service
    sudo systemctl enable $SERVICE_NAME
    
    success "Systemd service configured"
}

# Start the bot service
start_service() {
    info "Starting bot service..."
    
    # Stop service if running
    if systemctl is-active --quiet $SERVICE_NAME; then
        sudo systemctl stop $SERVICE_NAME
        sleep 2
    fi
    
    # Start service
    sudo systemctl start $SERVICE_NAME || error_exit "Failed to start bot service"
    
    # Wait for service to start
    sleep 3
    
    # Check service status
    if systemctl is-active --quiet $SERVICE_NAME; then
        success "Bot service started successfully"
    else
        error_exit "Bot service failed to start"
    fi
}

# Monitor service status
monitor_service() {
    info "Monitoring service status for 30 seconds..."
    
    for i in {1..6}; do
        if systemctl is-active --quiet $SERVICE_NAME; then
            info "Service is running (check $i/6)"
        else
            error_exit "Service stopped unexpectedly"
        fi
        sleep 5
    done
    
    success "Service monitoring completed - bot is stable"
}

# Show service information
show_service_info() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}     Football Coach Bot - Started!     ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Service status
    echo -e "${GREEN}Service Status:${NC}"
    sudo systemctl status $SERVICE_NAME --no-pager -l
    echo ""
    
    # Useful commands
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  View logs:        sudo journalctl -u $SERVICE_NAME -f"
    echo "  Restart service:  sudo systemctl restart $SERVICE_NAME"
    echo "  Stop service:     sudo systemctl stop $SERVICE_NAME"
    echo "  Service status:   sudo systemctl status $SERVICE_NAME"
    echo ""
    
    # Bot information
    cd "$BOT_DIR"
    source venv/bin/activate
    export $(cat .env | grep -v '^#' | xargs)
    
    echo -e "${GREEN}Bot Information:${NC}"
    echo "  Bot Directory:    $BOT_DIR"
    echo "  Service Name:     $SERVICE_NAME"
    echo "  User:             $BOT_USER"
    echo "  Database Mode:    ${USE_DATABASE:-JSON}"
    echo "  Debug Mode:       ${DEBUG:-false}"
    echo ""
}

# Main startup function
main() {
    echo -e "${BLUE}🚀 Football Coach Bot Startup Script${NC}"
    echo "======================================"
    
    log "Starting bot initialization..."
    
    # Run all checks and setup
    check_root
    check_requirements
    validate_environment
    test_database
    initialize_database
    test_telegram
    update_dependencies
    setup_systemd_service
    start_service
    monitor_service
    show_service_info
    
    log "Bot startup completed successfully!"
    success "🎉 Football Coach Bot is now running!"
}

# Handle script arguments
case "${1:-}" in
    "start")
        main
        ;;
    "restart")
        info "Restarting bot service..."
        sudo systemctl restart $SERVICE_NAME
        success "Bot service restarted"
        ;;
    "stop")
        info "Stopping bot service..."
        sudo systemctl stop $SERVICE_NAME
        success "Bot service stopped"
        ;;
    "status")
        sudo systemctl status $SERVICE_NAME
        ;;
    "logs")
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    "update")
        cd "$BOT_DIR"
        source venv/bin/activate
        update_dependencies
        sudo systemctl restart $SERVICE_NAME
        success "Bot updated and restarted"
        ;;
    *)
        echo "Usage: $0 {start|restart|stop|status|logs|update}"
        echo ""
        echo "Commands:"
        echo "  start   - Full initialization and startup"
        echo "  restart - Restart the bot service"
        echo "  stop    - Stop the bot service"
        echo "  status  - Show service status"
        echo "  logs    - Show live logs"
        echo "  update  - Update dependencies and restart"
        echo ""
        echo "For first-time setup, use: $0 start"
        exit 1
        ;;
esac
