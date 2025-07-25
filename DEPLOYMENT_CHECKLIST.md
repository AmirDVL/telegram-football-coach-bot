# 🚀 Production Deployment Security Checklist

## Pre-Deployment Checklist

### 🔐 Security Files
- [ ] `.env` file is NOT committed to git
- [ ] `.env.example` contains all required variables without sensitive data
- [ ] `.gitignore` includes all sensitive files and directories
- [ ] All sensitive data files are excluded from git

### 🤖 Bot Configuration
- [ ] `BOT_TOKEN` is set correctly in production `.env`
- [ ] `ADMIN_ID` is set to your Telegram user ID
- [ ] `DEBUG=false` in production environment
- [ ] Payment card details are configured correctly

### 💾 Database Security
- [ ] Strong database password is set
- [ ] Database user has minimum required permissions
- [ ] Database is not accessible from public internet
- [ ] Regular database backups are configured

### 🛡️ Server Security
- [ ] Server OS is updated to latest version
- [ ] Firewall is configured (SSH, HTTP, HTTPS only)
- [ ] SSH root login is disabled
- [ ] SSH key-based authentication is configured
- [ ] Dedicated bot user account is created
- [ ] File permissions are properly set (600 for .env, 700 for directories)

## Deployment Steps

### 1. Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3 python3-pip python3-venv git postgresql nginx fail2ban -y
```

### 2. Security Setup
```bash
# Run the security setup script
chmod +x security_setup.sh
sudo ./security_setup.sh
```

### 3. Bot Deployment
```bash
# Clone repository (without sensitive files)
sudo -u football-bot git clone <your-repo> /opt/football-bot

# Create virtual environment
sudo -u football-bot python3 -m venv /opt/football-bot/venv

# Install dependencies
sudo -u football-bot /opt/football-bot/venv/bin/pip install -r /opt/football-bot/requirements.txt

# Copy and configure environment
sudo -u football-bot cp /opt/football-bot/.env.example /opt/football-bot/.env
sudo -u football-bot nano /opt/football-bot/.env
```

### 4. Database Setup (if using PostgreSQL)
```bash
# Create database
sudo -u postgres createdb football_coach_bot_prod
sudo -u postgres createuser football_bot
sudo -u postgres psql -c "ALTER USER football_bot PASSWORD 'STRONG_PASSWORD_HERE';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE football_coach_bot_prod TO football_bot;"
```

### 5. Start Services
```bash
# Start and enable bot service
sudo systemctl start football-bot
sudo systemctl enable football-bot

# Check status
sudo systemctl status football-bot
```

## Post-Deployment Checklist

### 🔍 Verification
- [ ] Bot responds to `/start` command
- [ ] Payment flow works correctly
- [ ] Admin approval system functions
- [ ] Questionnaire system works after payment approval
- [ ] Database connections are working (if using PostgreSQL)
- [ ] Log files are being created properly

### 📊 Monitoring
- [ ] Bot service is running: `sudo systemctl status football-bot`
- [ ] Logs are clean: `sudo tail -f /var/log/football-bot/bot.log`
- [ ] Memory usage is normal: `sudo ps aux | grep python`
- [ ] Disk space is sufficient: `df -h`

### 🔒 Security Verification
- [ ] .env file is not accessible via web
- [ ] Database is not accessible from outside
- [ ] Only required ports are open: `sudo ufw status`
- [ ] Bot user has minimal permissions
- [ ] Backups are working: check `/opt/football-bot/backups/`

### 🔄 Maintenance Setup
- [ ] Automatic backups are scheduled
- [ ] Log rotation is configured
- [ ] Health monitoring is active
- [ ] Update procedure is documented

## Emergency Procedures

### Bot Not Responding
```bash
# Check service status
sudo systemctl status football-bot

# Restart service
sudo systemctl restart football-bot

# Check logs
sudo tail -f /var/log/football-bot/error.log
```

### Database Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Connect to database
sudo -u football-bot psql -h localhost -d football_coach_bot_prod

# Restore from backup (if needed)
sudo -u football-bot gunzip -c backup_YYYYMMDD_HHMMSS_db.sql.gz | psql -h localhost -d football_coach_bot_prod
```

### High Memory Usage
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Restart bot if needed
sudo systemctl restart football-bot
```

## Contact and Support

- **Bot Logs**: `/var/log/football-bot/bot.log`
- **Error Logs**: `/var/log/football-bot/error.log`
- **Backup Location**: `/opt/football-bot/backups/`
- **Service Control**: `sudo systemctl [start|stop|restart|status] football-bot`

## Security Best Practices Reminder

1. **Never commit sensitive files** to version control
2. **Use strong passwords** for all accounts
3. **Keep system updated** regularly
4. **Monitor logs** for suspicious activity
5. **Test backups** regularly
6. **Limit access** to production server
7. **Use HTTPS** for all web communications
8. **Rotate secrets** periodically
