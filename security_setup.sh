#!/bin/bash
# 🔒 Security Setup Script for Football Coach Bot
# Run this script on your server to set up proper security

echo "🛡️  Setting up security for Football Coach Bot..."

# Create bot user if it doesn't exist
if ! id "football-bot" &>/dev/null; then
    echo "👤 Creating football-bot user..."
    sudo adduser --system --group --home /opt/football-bot football-bot
fi

# Set proper file permissions
echo "📝 Setting file permissions..."
sudo chown -R football-bot:football-bot /opt/football-bot
sudo chmod 600 /opt/football-bot/.env
sudo chmod 700 /opt/football-bot
sudo chmod +x /opt/football-bot/main.py

# Create logs directory with proper permissions
echo "📋 Setting up logs directory..."
sudo mkdir -p /var/log/football-bot
sudo chown football-bot:football-bot /var/log/football-bot
sudo chmod 755 /var/log/football-bot

# Create data directory with restricted access
echo "💾 Setting up data directory..."
sudo mkdir -p /opt/football-bot/data
sudo chown football-bot:football-bot /opt/football-bot/data
sudo chmod 700 /opt/football-bot/data

# Setup firewall
echo "🔥 Configuring firewall..."
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Disable root login
echo "🚫 Securing SSH..."
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Setup log rotation
echo "🔄 Setting up log rotation..."
sudo tee /etc/logrotate.d/football-bot > /dev/null <<EOF
/var/log/football-bot/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    su football-bot football-bot
    postrotate
        systemctl reload football-bot
    endscript
}
EOF

# Create backup script
echo "💾 Creating backup script..."
sudo tee /opt/football-bot/backup.sh > /dev/null <<'EOF'
#!/bin/bash
# Backup script for Football Coach Bot

BACKUP_DIR="/opt/football-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_$DATE"

mkdir -p $BACKUP_DIR

# Backup data files
tar -czf "$BACKUP_DIR/${BACKUP_FILE}_data.tar.gz" /opt/football-bot/data/ 2>/dev/null

# Backup database if using PostgreSQL
if [ "$USE_DATABASE" = "true" ]; then
    pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/${BACKUP_FILE}_db.sql.gz"
fi

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup_*" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
EOF

sudo chmod +x /opt/football-bot/backup.sh
sudo chown football-bot:football-bot /opt/football-bot/backup.sh

# Setup automatic backups
echo "⏰ Setting up automatic backups..."
(sudo crontab -u football-bot -l 2>/dev/null; echo "0 2 * * * /opt/football-bot/backup.sh") | sudo crontab -u football-bot -

# Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/football-bot.service > /dev/null <<EOF
[Unit]
Description=Football Coach Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=football-bot
Group=football-bot
WorkingDirectory=/opt/football-bot
Environment=PATH=/opt/football-bot/venv/bin
ExecStart=/opt/football-bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=file:/var/log/football-bot/bot.log
StandardError=file:/var/log/football-bot/error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/football-bot /var/log/football-bot

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable football-bot

# Create monitoring script
echo "📊 Creating monitoring script..."
sudo tee /opt/football-bot/monitor.sh > /dev/null <<'EOF'
#!/bin/bash
# Monitoring script for Football Coach Bot

# Check if bot is running
if ! systemctl is-active --quiet football-bot; then
    echo "⚠️  Bot is not running! Attempting restart..."
    systemctl restart football-bot
    sleep 10
    if systemctl is-active --quiet football-bot; then
        echo "✅ Bot restarted successfully"
    else
        echo "❌ Failed to restart bot"
        exit 1
    fi
fi

# Check memory usage
MEMORY_USAGE=$(ps -o pid,ppid,cmd,%mem --sort=-%mem -C python | grep main.py | awk '{print $4}')
if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "⚠️  High memory usage: ${MEMORY_USAGE}%"
fi

# Check disk space
DISK_USAGE=$(df /opt/football-bot | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "⚠️  Low disk space: ${DISK_USAGE}% used"
fi

echo "✅ Bot health check completed"
EOF

sudo chmod +x /opt/football-bot/monitor.sh
sudo chown football-bot:football-bot /opt/football-bot/monitor.sh

# Setup monitoring cron job
(sudo crontab -u football-bot -l 2>/dev/null; echo "*/5 * * * * /opt/football-bot/monitor.sh") | sudo crontab -u football-bot -

echo "✅ Security setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Copy your bot files to /opt/football-bot/"
echo "2. Create and configure /opt/football-bot/.env"
echo "3. Install Python dependencies: pip install -r requirements.txt"
echo "4. Start the bot: sudo systemctl start football-bot"
echo "5. Check status: sudo systemctl status football-bot"
echo ""
echo "🔒 Security features enabled:"
echo "- Dedicated bot user with restricted permissions"
echo "- Firewall configured"
echo "- SSH root login disabled"
echo "- Log rotation configured"
echo "- Automatic backups (daily at 2 AM)"
echo "- Health monitoring (every 5 minutes)"
echo "- Systemd service with security restrictions"
