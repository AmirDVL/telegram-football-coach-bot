#!/bin/bash

# 🔧 Football Coach Bot - Management Utility Script
# Provides easy commands for managing the bot service

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

show_help() {
    echo "Football Coach Bot Management Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  status      Show bot service status"
    echo "  start       Start the bot service"
    echo "  stop        Stop the bot service"
    echo "  restart     Restart the bot service"
    echo "  logs        Show real-time bot logs"
    echo "  logs-tail   Show last 50 lines of bot logs"
    echo "  backup      Create manual database backup"
    echo "  update      Update bot code from git and restart"
    echo "  monitor     Show resource usage and system info"
    echo "  check       Run health checks"
    echo "  help        Show this help message"
    echo
}

check_service_status() {
    if systemctl is-active --quiet $BOT_SERVICE; then
        return 0
    else
        return 1
    fi
}

cmd_status() {
    print_status "Checking bot service status..."
    systemctl status $BOT_SERVICE --no-pager -l
}

cmd_start() {
    print_status "Starting bot service..."
    systemctl start $BOT_SERVICE
    sleep 2
    if check_service_status; then
        print_success "Bot started successfully"
    else
        print_error "Failed to start bot"
        exit 1
    fi
}

cmd_stop() {
    print_status "Stopping bot service..."
    systemctl stop $BOT_SERVICE
    sleep 2
    if ! check_service_status; then
        print_success "Bot stopped successfully"
    else
        print_error "Failed to stop bot"
        exit 1
    fi
}

cmd_restart() {
    print_status "Restarting bot service..."
    systemctl restart $BOT_SERVICE
    sleep 3
    if check_service_status; then
        print_success "Bot restarted successfully"
    else
        print_error "Failed to restart bot"
        exit 1
    fi
}

cmd_logs() {
    print_status "Showing real-time bot logs (Press Ctrl+C to exit)..."
    journalctl -u $BOT_SERVICE -f
}

cmd_logs_tail() {
    print_status "Showing last 50 lines of bot logs..."
    journalctl -u $BOT_SERVICE -n 50 --no-pager
}

cmd_backup() {
    print_status "Creating manual database backup..."
    if [[ -f "$BOT_DIR/backup.sh" ]]; then
        sudo -u $BOT_USER $BOT_DIR/backup.sh
        print_success "Backup completed"
    else
        print_error "Backup script not found at $BOT_DIR/backup.sh"
        exit 1
    fi
}

cmd_update() {
    print_status "Updating bot from git repository..."
    
    if [[ ! -d "$BOT_DIR/.git" ]]; then
        print_error "Bot directory is not a git repository"
        exit 1
    fi
    
    # Stop the service
    print_status "Stopping bot service..."
    systemctl stop $BOT_SERVICE
    
    # Backup current state
    cmd_backup
    
    # Update code
    print_status "Pulling latest changes..."
    cd $BOT_DIR
    sudo -u $BOT_USER git pull origin main
    
    # Update dependencies if requirements.txt exists
    if [[ -f "$BOT_DIR/requirements.txt" ]]; then
        print_status "Updating dependencies..."
        sudo -u $BOT_USER bash -c "cd $BOT_DIR && source venv/bin/activate && pip install -r requirements.txt"
    fi
    
    # Start the service
    print_status "Starting bot service..."
    systemctl start $BOT_SERVICE
    
    sleep 3
    if check_service_status; then
        print_success "Bot updated and restarted successfully"
    else
        print_error "Bot failed to start after update"
        print_status "Check logs: $0 logs"
        exit 1
    fi
}

cmd_monitor() {
    print_status "System and Bot Monitoring Information"
    echo
    
    # System info
    echo -e "${BLUE}=== System Information ===${NC}"
    echo "Hostname: $(hostname)"
    echo "Uptime: $(uptime -p)"
    echo "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
    echo
    
    # Memory usage
    echo -e "${BLUE}=== Memory Usage ===${NC}"
    free -h
    echo
    
    # Disk usage
    echo -e "${BLUE}=== Disk Usage ===${NC}"
    df -h /
    echo
    
    # Bot service info
    echo -e "${BLUE}=== Bot Service Information ===${NC}"
    if check_service_status; then
        echo -e "Status: ${GREEN}RUNNING${NC}"
        echo "Memory Usage: $(ps -o pid,rss,command -p $(systemctl show --property MainPID --value $BOT_SERVICE) | tail -n 1 | awk '{print $2/1024 " MB"}')"
        echo "Started: $(systemctl show --property ActiveEnterTimestamp --value $BOT_SERVICE)"
    else
        echo -e "Status: ${RED}STOPPED${NC}"
    fi
    echo
    
    # Database info
    echo -e "${BLUE}=== Database Information ===${NC}"
    if systemctl is-active --quiet postgresql; then
        echo -e "PostgreSQL: ${GREEN}RUNNING${NC}"
        sudo -u postgres psql -c "SELECT count(*) as active_connections FROM pg_stat_activity;" 2>/dev/null || echo "Could not connect to database"
    else
        echo -e "PostgreSQL: ${RED}STOPPED${NC}"
    fi
    echo
    
    # Recent errors
    echo -e "${BLUE}=== Recent Bot Errors (if any) ===${NC}"
    journalctl -u $BOT_SERVICE --since "1 hour ago" -p err --no-pager | head -10
}

cmd_check() {
    print_status "Running health checks..."
    echo
    
    local errors=0
    
    # Check if service is running
    echo -n "Bot service status... "
    if check_service_status; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        errors=$((errors + 1))
    fi
    
    # Check database connection
    echo -n "Database connection... "
    if systemctl is-active --quiet postgresql; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        errors=$((errors + 1))
    fi
    
    # Check bot directory
    echo -n "Bot directory permissions... "
    if [[ -d "$BOT_DIR" ]] && [[ -O "$BOT_DIR" || $(stat -c %U "$BOT_DIR") == "$BOT_USER" ]]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        errors=$((errors + 1))
    fi
    
    # Check environment file
    echo -n "Environment file... "
    if [[ -f "$BOT_DIR/.env" ]]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        errors=$((errors + 1))
    fi
    
    # Check virtual environment
    echo -n "Python virtual environment... "
    if [[ -d "$BOT_DIR/venv" ]] && [[ -f "$BOT_DIR/venv/bin/python" ]]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        errors=$((errors + 1))
    fi
    
    # Check disk space
    echo -n "Disk space (root partition)... "
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [[ $disk_usage -lt 90 ]]; then
        echo -e "${GREEN}OK ($disk_usage% used)${NC}"
    else
        echo -e "${YELLOW}WARNING ($disk_usage% used)${NC}"
    fi
    
    echo
    if [[ $errors -eq 0 ]]; then
        print_success "All health checks passed!"
    else
        print_error "$errors health check(s) failed"
        exit 1
    fi
}

# Main script logic
case "$1" in
    status)
        cmd_status
        ;;
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    logs)
        cmd_logs
        ;;
    logs-tail)
        cmd_logs_tail
        ;;
    backup)
        cmd_backup
        ;;
    update)
        cmd_update
        ;;
    monitor)
        cmd_monitor
        ;;
    check)
        cmd_check
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac
