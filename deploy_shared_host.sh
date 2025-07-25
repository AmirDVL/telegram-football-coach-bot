#!/bin/bash

# 🚀 Football Coach Bot - Shared Host Deployment Script
# This script helps you deploy the bot on your existing Linux hosting

echo "🤖 Football Coach Bot - Shared Host Deployment"
echo "=============================================="

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

# Check if we're on the correct host
echo ""
print_status "Checking system requirements..."

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_success "Python 3 found: $PYTHON_VERSION"
    
    # Check if version is 3.8+
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_success "Python version is compatible (3.8+)"
    else
        print_error "Python version is too old. Need 3.8+, found $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    print_success "pip3 found"
else
    print_warning "pip3 not found. Trying to install..."
    python3 -m ensurepip --default-pip
fi

# Check available memory
MEMORY=$(free -m | awk 'NR==2{printf "%.0f", $7}')
if [ "$MEMORY" -gt 200 ]; then
    print_success "Available memory: ${MEMORY}MB"
else
    print_warning "Low available memory: ${MEMORY}MB. Bot may face memory issues."
fi

# Check for screen or tmux
if command -v screen &> /dev/null; then
    PROCESS_MANAGER="screen"
    print_success "Screen found - will use for background process"
elif command -v tmux &> /dev/null; then
    PROCESS_MANAGER="tmux"
    print_success "Tmux found - will use for background process"
else
    PROCESS_MANAGER="nohup"
    print_warning "Neither screen nor tmux found. Will use nohup (less reliable)"
fi

echo ""
print_status "Setting up bot environment..."

# Create virtual environment if possible
if python3 -m venv --help &> /dev/null; then
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    print_status "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
else
    print_warning "Virtual environment not supported. Installing globally."
fi

# Install dependencies
print_status "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --user
    if [ $? -eq 0 ]; then
        print_success "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
else
    print_error "requirements.txt not found"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your bot token and configuration"
        print_warning "Run: nano .env"
        echo ""
        echo "Required variables to set:"
        echo "- BOT_TOKEN=your_telegram_bot_token"
        echo "- ADMIN_ID=your_telegram_user_id"
        echo ""
        read -p "Press Enter after you've configured .env file..."
    else
        print_error ".env.example not found. Please create .env file manually."
        exit 1
    fi
fi

# Validate .env file
if grep -q "your_bot_token_here" .env || grep -q "your_telegram_user_id" .env; then
    print_error "Please configure .env file with actual values"
    exit 1
fi

print_success "Environment configuration completed"

echo ""
print_status "Creating deployment scripts..."

# Create start script
cat > start_bot.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start bot
python3 main.py
EOF

chmod +x start_bot.sh
print_success "Created start_bot.sh"

# Create stop script
cat > stop_bot.sh << 'EOF'
#!/bin/bash
echo "Stopping Football Coach Bot..."

# Kill python processes running main.py
pkill -f "python3 main.py"
pkill -f "python main.py"

# Kill screen sessions
screen -ls | grep football_bot | cut -d. -f1 | awk '{print $1}' | xargs -I {} screen -X -S {} quit 2>/dev/null

echo "Bot stopped"
EOF

chmod +x stop_bot.sh
print_success "Created stop_bot.sh"

# Create status script
cat > status_bot.sh << 'EOF'
#!/bin/bash
echo "🤖 Football Coach Bot Status"
echo "=========================="

# Check if bot process is running
if pgrep -f "python3 main.py" > /dev/null; then
    echo "✅ Bot is RUNNING"
    echo ""
    echo "Process info:"
    ps aux | grep "python3 main.py" | grep -v grep
    echo ""
    echo "Memory usage:"
    ps -o pid,ppid,%mem,%cpu,comm -p $(pgrep -f "python3 main.py")
else
    echo "❌ Bot is NOT running"
fi

echo ""
echo "Recent log entries:"
if [ -f "bot.log" ]; then
    tail -10 bot.log
else
    echo "No log file found"
fi
EOF

chmod +x status_bot.sh
print_success "Created status_bot.sh"

# Create restart script for cron
cat > restart_bot.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

# Check if bot is running
if ! pgrep -f "python3 main.py" > /dev/null; then
    echo "$(date): Bot not running, starting..." >> restart.log
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Start bot in background
    if command -v screen &> /dev/null; then
        screen -dmS football_bot python3 main.py
    elif command -v tmux &> /dev/null; then
        tmux new-session -d -s football_bot python3 main.py
    else
        nohup python3 main.py > bot.log 2>&1 &
    fi
    
    echo "$(date): Bot started" >> restart.log
else
    echo "$(date): Bot is running" >> restart.log
fi
EOF

chmod +x restart_bot.sh
print_success "Created restart_bot.sh"

echo ""
print_status "Starting the bot..."

# Start bot based on available process manager
case $PROCESS_MANAGER in
    "screen")
        print_status "Starting bot in screen session..."
        screen -dmS football_bot ./start_bot.sh
        sleep 2
        if screen -ls | grep -q football_bot; then
            print_success "Bot started in screen session 'football_bot'"
            print_status "To view bot: screen -r football_bot"
            print_status "To detach: Ctrl+A, then D"
        else
            print_error "Failed to start bot in screen"
        fi
        ;;
    "tmux")
        print_status "Starting bot in tmux session..."
        tmux new-session -d -s football_bot ./start_bot.sh
        sleep 2
        if tmux ls | grep -q football_bot; then
            print_success "Bot started in tmux session 'football_bot'"
            print_status "To view bot: tmux attach -t football_bot"
            print_status "To detach: Ctrl+B, then D"
        else
            print_error "Failed to start bot in tmux"
        fi
        ;;
    "nohup")
        print_status "Starting bot with nohup..."
        nohup ./start_bot.sh > bot.log 2>&1 &
        sleep 2
        if pgrep -f "python3 main.py" > /dev/null; then
            print_success "Bot started with nohup"
            print_status "Check logs: tail -f bot.log"
        else
            print_error "Failed to start bot with nohup"
        fi
        ;;
esac

# Check if bot is actually running
sleep 3
if pgrep -f "python3 main.py" > /dev/null; then
    print_success "🎉 Bot is running successfully!"
else
    print_error "Bot failed to start. Check the logs."
    if [ -f "bot.log" ]; then
        echo ""
        echo "Recent log entries:"
        tail -20 bot.log
    fi
    exit 1
fi

echo ""
print_status "Setting up auto-restart (cron job)..."

# Check if crontab is available
if command -v crontab &> /dev/null; then
    BOT_PATH=$(pwd)
    CRON_JOB="*/5 * * * * $BOT_PATH/restart_bot.sh"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "restart_bot.sh"; then
        print_warning "Cron job already exists"
    else
        # Add cron job
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        if [ $? -eq 0 ]; then
            print_success "Auto-restart cron job added (checks every 5 minutes)"
        else
            print_warning "Failed to add cron job. Add manually:"
            echo "crontab -e"
            echo "Add: $CRON_JOB"
        fi
    fi
else
    print_warning "Crontab not available. Auto-restart not configured."
fi

echo ""
print_success "🎉 Deployment completed successfully!"
echo ""
echo "📋 Management Commands:"
echo "  Start bot:    ./start_bot.sh"
echo "  Stop bot:     ./stop_bot.sh"
echo "  Check status: ./status_bot.sh"
echo "  View logs:    tail -f bot.log"

if [ "$PROCESS_MANAGER" = "screen" ]; then
    echo "  Attach to bot: screen -r football_bot"
elif [ "$PROCESS_MANAGER" = "tmux" ]; then
    echo "  Attach to bot: tmux attach -t football_bot"
fi

echo ""
echo "📊 Current Status:"
./status_bot.sh

echo ""
print_status "Deployment complete! Your bot should now be running on this host."
print_status "Monitor the logs and performance over the next few days."
print_warning "If you experience issues, consider upgrading to a dedicated VPS."
