#!/bin/bash

# Football Coach Bot - Server Bootstrap Script
# Run this script on a fresh server to set up everything automatically

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BOT_USER="footballbot"
BOT_DIR="/opt/football-bot"
REPO_URL="https://github.com/AmirDVL/telegram-football-coach-bot.git"

echo -e "${BLUE}🚀 Football Coach Bot - Server Bootstrap${NC}"
echo "========================================"
echo ""

# Function to prompt for input
prompt_input() {
    local prompt="$1"
    local var_name="$2"
    local default="$3"
    
    if [[ -n "$default" ]]; then
        read -p "$prompt [$default]: " input
        eval "$var_name=\"\${input:-$default}\""
    else
        read -p "$prompt: " input
        eval "$var_name=\"$input\""
    fi
}

# Collect configuration
echo -e "${YELLOW}📝 Configuration Setup${NC}"
echo "Please provide the following information:"
echo ""

prompt_input "Bot Token (from @BotFather)" "BOT_TOKEN"
prompt_input "Admin Telegram User ID" "ADMIN_ID"
prompt_input "Database Password" "DB_PASSWORD"
prompt_input "Use Database (true/false)" "USE_DATABASE" "true"

echo ""
echo -e "${BLUE}🔧 Starting server setup...${NC}"

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "📦 Installing essential packages..."
sudo apt install -y curl wget git nano htop unzip software-properties-common \
    apt-transport-https ca-certificates gnupg lsb-release python3 python3-pip \
    python3-venv python3-dev build-essential libffi-dev libssl-dev libpq-dev \
    postgresql postgresql-contrib fail2ban dnsutils

# Create bot user
echo "👤 Creating bot user..."
if ! id "$BOT_USER" &>/dev/null; then
    sudo adduser --system --group --home "$BOT_DIR" --shell /bin/bash "$BOT_USER"
    sudo usermod -aG sudo "$BOT_USER"
fi

# Create bot directory
sudo mkdir -p "$BOT_DIR"
sudo chown "$BOT_USER:$BOT_USER" "$BOT_DIR"

# Setup PostgreSQL
echo "🗄️ Setting up PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE IF NOT EXISTS football_coach_bot;
CREATE USER IF NOT EXISTS footballbot_app WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE football_coach_bot TO footballbot_app;
\q
EOF

# Configure PostgreSQL for security
echo "🔐 Configuring PostgreSQL security..."
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /etc/postgresql/*/main/postgresql.conf
sudo sed -i "s/#password_encryption = md5/password_encryption = scram-sha-256/" /etc/postgresql/*/main/postgresql.conf
sudo systemctl restart postgresql

# Setup firewall
echo "🔥 Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow out 443
sudo ufw allow out 80

# Clone repository
echo "📥 Cloning bot repository..."
sudo -u "$BOT_USER" git clone "$REPO_URL" "$BOT_DIR/temp"
sudo -u "$BOT_USER" mv "$BOT_DIR/temp/"* "$BOT_DIR/" 2>/dev/null || true
sudo -u "$BOT_USER" mv "$BOT_DIR/temp/."* "$BOT_DIR/" 2>/dev/null || true
sudo -u "$BOT_USER" rmdir "$BOT_DIR/temp" 2>/dev/null || true

# Setup Python environment
echo "🐍 Setting up Python environment..."
sudo -u "$BOT_USER" python3 -m venv "$BOT_DIR/venv"
sudo -u "$BOT_USER" bash -c "cd '$BOT_DIR' && source venv/bin/activate && pip install --upgrade pip"
sudo -u "$BOT_USER" bash -c "cd '$BOT_DIR' && source venv/bin/activate && pip install python-telegram-bot python-dotenv aiofiles asyncpg pillow"

# Create environment file
echo "⚙️ Creating environment configuration..."
sudo -u "$BOT_USER" tee "$BOT_DIR/.env" > /dev/null <<EOF
# Telegram Bot Configuration
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID

# Database Configuration
USE_DATABASE=$USE_DATABASE
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_coach_bot
DB_USER=footballbot_app
DB_PASSWORD=$DB_PASSWORD

# Production Settings
DEBUG=false

# Security Settings
MAX_REQUESTS_PER_MINUTE=60
RATE_LIMIT_ENABLED=true
LOG_LEVEL=INFO
EOF

# Set secure permissions
sudo chmod 600 "$BOT_DIR/.env"
sudo chown "$BOT_USER:$BOT_USER" "$BOT_DIR/.env"

# Make startup script executable
sudo chmod +x "$BOT_DIR/startup.sh"

echo ""
echo -e "${GREEN}✅ Server bootstrap completed!${NC}"
echo ""
echo -e "${YELLOW}🚀 Next Steps:${NC}"
echo "1. Run the startup script: sudo -u $BOT_USER $BOT_DIR/startup.sh start"
echo "2. Check service status:   sudo systemctl status football-bot"
echo "3. View logs:              sudo journalctl -u football-bot -f"
echo ""
echo -e "${BLUE}📱 Test your bot by sending /start on Telegram!${NC}"
