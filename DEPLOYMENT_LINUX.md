# 🚀 Football Coach Bot - Linux Server Deployment Guide

This guide will help you deploy the Football Coach Bot with PostgreSQL database on a fresh Linux server.

## Prerequisites

- Fresh Linux server (Debian 11+, Ubuntu 20.04+, CentOS 8+, or RHEL 8+)
- Root access or sudo privileges
- Internet connection
- Telegram Bot Token (from @BotFather)
- Your Telegram User ID (get from @userinfobot)

## 🎯 Quick Production Deployment

### Option 1: Automated Production Deployment (Recommended)

```bash
# Download the latest deployment script
wget https://raw.githubusercontent.com/your-username/football-coach-bot/main/deploy_production.sh

# Make it executable
chmod +x deploy_production.sh

# Run the deployment script
sudo bash deploy_production.sh
```

The production deployment script will:
- ✅ Detect your Linux distribution automatically
- ✅ Update the system and install dependencies
- ✅ Install and configure PostgreSQL database
- ✅ Create dedicated bot user for security
- ✅ Set up Python virtual environment
- ✅ Configure PostgreSQL database with proper permissions
- ✅ Create and configure systemd service
- ✅ Set up automated backups (daily at 2 AM)
- ✅ Configure log rotation
- ✅ Set up firewall rules
- ✅ Create management scripts
- ✅ Initialize database with admin user
- ✅ Start the bot service

### Option 2: Standard Debian/Ubuntu Deployment

```bash
# Clone the repository
git clone <your-repo-url> /tmp/football-bot
cd /tmp/football-bot

# Make scripts executable
chmod +x setup_debian.sh manage.sh update.sh

# Run the setup script
sudo bash setup_debian.sh
```

## 🗄️ Database Configuration

The bot now uses **PostgreSQL** as the primary database with the following benefits:

### PostgreSQL Features:
- ✅ **Persistent data storage** - No data loss on restarts
- ✅ **ACID compliance** - Data integrity guaranteed
- ✅ **Concurrent access** - Multiple processes can access safely
- ✅ **Backup and recovery** - Automated daily backups
- ✅ **Scalability** - Handles thousands of users
- ✅ **Persian text support** - Full UTF-8 support

### Database Setup:
```sql
-- Database: football_coach_bot
-- User: footballbot
-- Tables: users, payments, admins, user_responses, statistics
```

## 🔧 Manual Installation (Advanced Users)

If you prefer manual installation:
```bash
# Create database and user
sudo -u postgres createdb football_coach_bot
sudo -u postgres createuser footballbot
sudo -u postgres psql -c "ALTER USER footballbot WITH ENCRYPTED PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE football_coach_bot TO footballbot;"
```

### 3. Bot Setup
```bash
# Create bot user and directory
sudo adduser --system --group --home /opt/football-bot footballbot
sudo mkdir -p /opt/football-bot
sudo chown footballbot:footballbot /opt/football-bot

# Deploy code
sudo cp -r ./* /opt/football-bot/
sudo chown -R footballbot:footballbot /opt/football-bot

# Set up Python environment
sudo -u footballbot bash -c "cd /opt/football-bot && python3 -m venv venv"
sudo -u footballbot bash -c "cd /opt/football-bot && source venv/bin/activate && pip install -r requirements.txt"

# Create environment file
sudo -u footballbot tee /opt/football-bot/.env << EOF
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_user_id
USE_DATABASE=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_coach_bot
DB_USER=footballbot
DB_PASSWORD=your_secure_password
DEBUG=false
EOF
```

### 4. Systemd Service
```bash
# Create service file
sudo tee /etc/systemd/system/football-bot.service << EOF
[Unit]
Description=Football Coach Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=footballbot
WorkingDirectory=/opt/football-bot
ExecStart=/opt/football-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable football-bot
sudo systemctl start football-bot
```

## Management Commands

After deployment, use the management script:

```bash
# Make management script accessible system-wide
sudo cp manage.sh /usr/local/bin/botctl
sudo chmod +x /usr/local/bin/botctl

# Usage examples
botctl status      # Check bot status
botctl logs        # View real-time logs
botctl restart     # Restart the bot
botctl backup      # Create manual backup
botctl monitor     # View system information
botctl check       # Run health checks
botctl update      # Update bot from git
```

## Important Files and Directories

```
/opt/football-bot/              # Main bot directory
├── main.py                     # Bot main file
├── questionnaire_manager.py    # Questionnaire logic
├── database_manager.py         # Database operations
├── .env                        # Environment variables (sensitive!)
├── venv/                       # Python virtual environment
├── backups/                    # Database backups
├── manage.sh                   # Management script
└── requirements.txt            # Python dependencies

/etc/systemd/system/football-bot.service  # Systemd service
/var/log/journal/                          # Service logs
```

## Monitoring and Maintenance

### View Logs
```bash
# Real-time logs
sudo journalctl -u football-bot -f

# Last 50 lines
sudo journalctl -u football-bot -n 50
```

### Service Management
```bash
sudo systemctl status football-bot    # Check status
sudo systemctl restart football-bot   # Restart
sudo systemctl stop football-bot      # Stop
sudo systemctl start football-bot     # Start
```

### Database Backup
```bash
# Manual backup
sudo -u footballbot /opt/football-bot/backup.sh

# Automated backups run daily at 2 AM via cron
```

### Updates
```bash
# Update system and bot
sudo bash /opt/football-bot/update.sh

# Or use management script
botctl update
```

## Security Notes

1. **Firewall**: Only open necessary ports (22 for SSH, 443/80 for web if needed)
2. **Bot Token**: Keep your .env file secure, never commit it to version control
3. **Database**: Use strong passwords and consider restricting database access
4. **Updates**: Keep the system and bot dependencies updated regularly
5. **Backups**: Monitor backup success and test restoration procedures

## Troubleshooting

### Bot Won't Start
```bash
# Check service status
sudo systemctl status football-bot

# Check logs for errors
sudo journalctl -u football-bot -n 20

# Check configuration
sudo -u footballbot cat /opt/football-bot/.env
```

### Database Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u footballbot psql -h localhost -U footballbot -d football_coach_bot -c "SELECT version();"
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R footballbot:footballbot /opt/football-bot

# Check file permissions
ls -la /opt/football-bot/
```

## Support

If you encounter issues:

1. Check the logs: `sudo journalctl -u football-bot -f`
2. Run health checks: `botctl check`
3. Verify configuration: `botctl monitor`
4. Create an issue in the GitHub repository with error logs

## Performance Optimization

For high-traffic bots:

1. **Database Optimization**: Configure PostgreSQL for your workload
2. **Resource Monitoring**: Use `botctl monitor` to track resource usage
3. **Log Management**: Adjust log rotation settings if needed
4. **Backup Strategy**: Consider off-site backup storage for production

---

**Success!** 🎉 Your Football Coach Bot should now be running on your Linux server!

Test it by sending `/start` to your bot on Telegram.
