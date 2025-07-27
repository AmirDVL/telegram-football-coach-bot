#!/bin/bash

# 🔧 Football Coach Bot - Quick Setup Script
# Use this when you've manually uploaded files to the server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Configuration
BOT_DIR="/opt/football-bot"
BOT_USER="footballbot"

# Check if we're in the right directory
check_directory() {
    if [ ! -f "main.py" ]; then
        print_error "main.py not found in current directory"
        print_status "Please run this script from your bot directory containing main.py"
        exit 1
    fi
    print_success "Found main.py - correct directory confirmed"
}

# Setup Python virtual environment
setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    
    print_success "Virtual environment created"
}

# Install dependencies
install_deps() {
    print_status "Installing Python dependencies..."
    
    source venv/bin/activate
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencies installed from requirements.txt"
    else
        print_warning "requirements.txt not found, installing essential packages..."
        pip install python-telegram-bot==21.0.1 aiofiles asyncpg python-dotenv
        print_success "Essential dependencies installed"
    fi
}

# Configure environment
setup_env() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_status "Copied .env.example to .env"
        else
            # Create basic .env file
            cat > .env <<EOF
# Telegram Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_ID=YOUR_TELEGRAM_USER_ID

# Database Configuration
USE_DATABASE=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_coach_bot
DB_USER=footballbot
DB_PASSWORD=YOUR_DB_PASSWORD_HERE

# Production Settings
DEBUG=false
EOF
            print_status "Created basic .env file"
        fi
        
        chmod 600 .env
        print_warning "Please edit .env file with your configuration:"
        print_status "nano .env"
    else
        print_success ".env file already exists"
    fi
}

# Test bot startup
test_startup() {
    print_status "Testing bot startup..."
    
    source venv/bin/activate
    
    # Check if configuration is complete
    if grep -q "YOUR_BOT_TOKEN_HERE" .env; then
        print_warning "Bot token not configured in .env file"
        print_status "Please edit .env and add your BOT_TOKEN before testing"
        return
    fi
    
    print_status "Running quick startup test..."
    timeout 10s python3 main.py || {
        if [ $? -eq 124 ]; then
            print_success "Bot started successfully (test timeout reached)"
        else
            print_error "Bot startup failed"
            print_status "Check your configuration and try again"
        fi
    }
}

# Initialize database
init_database() {
    print_status "Initializing database schema..."
    
    source venv/bin/activate
    
    if [ -f "database_manager.py" ]; then
        python3 -c "
import asyncio
import sys
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
    print(f'Database initialization error: {e}')
    print('Please check your database configuration in .env')
    sys.exit(1)
"
        print_success "Database schema initialized"
    else
        print_warning "database_manager.py not found, skipping database initialization"
    fi
}

# Show next steps
show_next_steps() {
    print_success "=== QUICK SETUP COMPLETED ==="
    echo
    print_status "Next steps:"
    echo "1. Edit configuration:"
    echo "   nano .env"
    echo
    echo "2. Test the bot:"
    echo "   source venv/bin/activate"
    echo "   python3 main.py"
    echo
    echo "3. Set up as system service (optional):"
    echo "   sudo systemctl enable football-bot"
    echo "   sudo systemctl start football-bot"
    echo
    print_status "Configuration files:"
    echo "- Bot config: .env"
    echo "- Python environment: venv/"
    echo "- Main script: main.py"
    echo
    print_success "🎉 Bot is ready to run!"
}

# Main execution
main() {
    echo "🔧 Football Coach Bot - Quick Setup"
    echo "=================================="
    echo
    
    check_directory
    setup_venv
    install_deps
    setup_env
    init_database
    test_startup
    
    echo
    show_next_steps
}

# Run main function
main "$@"
