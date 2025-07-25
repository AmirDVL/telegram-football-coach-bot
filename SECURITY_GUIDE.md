# 🛡️ Security Configuration Guide

## 🚨 CRITICAL SECURITY NOTICE

**Before uploading to ANY public repository or server, ensure ALL sensitive data is removed!**

## 🔒 Pre-Upload Security Checklist

### ✅ Essential Files Created/Updated:

1. **`.gitignore`** - Prevents sensitive files from being committed
2. **`.env.example`** - Template for environment variables (NO sensitive data)
3. **`security_setup.sh`** - Automated server security configuration
4. **`DEPLOYMENT_CHECKLIST.md`** - Complete deployment guide

### 🚫 Files That Should NEVER Be Uploaded:

- `.env` (contains your bot token and secrets)
- `user_data.json` (contains user information)
- `payments.json` (contains payment data)
- `admin_data.json` (contains admin information)
- `questionnaire_data.json` (contains user responses)
- Any `*.log` files
- Any `*.db` or `*.sqlite` files

## 🔧 Server Setup Instructions

### 1. Initial Server Setup

```bash
# On your server, download the security setup script
wget https://raw.githubusercontent.com/yourusername/yourrepo/main/security_setup.sh

# Make it executable and run
chmod +x security_setup.sh
sudo ./security_setup.sh
```

### 2. Deploy Your Bot

```bash
# Clone your repository
sudo -u football-bot git clone https://github.com/yourusername/yourrepo.git /opt/football-bot

# Create virtual environment
sudo -u football-bot python3 -m venv /opt/football-bot/venv

# Install dependencies
sudo -u football-bot /opt/football-bot/venv/bin/pip install -r /opt/football-bot/requirements.txt

# Create environment file from template
sudo -u football-bot cp /opt/football-bot/.env.example /opt/football-bot/.env

# Edit with your actual credentials
sudo -u football-bot nano /opt/football-bot/.env
```

### 3. Configure Environment Variables

Edit `/opt/football-bot/.env` with your actual values:

```bash
BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ  # From @BotFather
ADMIN_ID=123456789  # Your Telegram user ID
USE_DATABASE=true  # Use PostgreSQL in production
DB_PASSWORD=your_very_secure_password
PAYMENT_CARD_NUMBER=your_actual_card_number
PAYMENT_CARD_HOLDER=Your Real Name
```

### 4. Start the Bot

```bash
# Start the service
sudo systemctl start football-bot

# Enable auto-start on boot
sudo systemctl enable football-bot

# Check status
sudo systemctl status football-bot
```

## 🔍 Verification Steps

### Test Bot Functionality:
1. Send `/start` to your bot
2. Try selecting a course
3. Test payment flow
4. Verify admin approval works
5. Check questionnaire after payment approval

### Check Security:
```bash
# Verify file permissions
ls -la /opt/football-bot/.env  # Should show 600 permissions
ls -la /opt/football-bot/      # Should be owned by football-bot

# Check firewall
sudo ufw status  # Should show limited open ports

# Verify service security
sudo systemctl show football-bot | grep -E "(User=|Group=|NoNewPrivileges=)"
```

## 📊 Monitoring Commands

```bash
# Check bot logs
sudo journalctl -u football-bot -f

# Monitor system resources
htop

# Check disk space
df -h

# View error logs
sudo tail -f /var/log/football-bot/error.log
```

## 🔄 Update Procedure

```bash
# Stop bot
sudo systemctl stop football-bot

# Backup current version
sudo cp -r /opt/football-bot /opt/football-bot.backup.$(date +%Y%m%d)

# Pull updates
sudo -u football-bot git pull

# Update dependencies if needed
sudo -u football-bot /opt/football-bot/venv/bin/pip install -r requirements.txt

# Start bot
sudo systemctl start football-bot
```

## 🆘 Troubleshooting

### Bot Won't Start
```bash
# Check service status
sudo systemctl status football-bot

# Check logs
sudo journalctl -u football-bot -n 50

# Verify environment file
sudo -u football-bot cat /opt/football-bot/.env
```

### Database Connection Issues
```bash
# Test database connection
sudo -u football-bot psql -h localhost -U football_bot -d football_coach_bot_prod

# Check PostgreSQL status
sudo systemctl status postgresql
```

### Permission Errors
```bash
# Fix ownership
sudo chown -R football-bot:football-bot /opt/football-bot

# Fix permissions
sudo chmod 600 /opt/football-bot/.env
sudo chmod 700 /opt/football-bot
```

## ⚠️ Security Reminders

1. **Never share your .env file** - it contains sensitive credentials
2. **Use strong passwords** for database and server access
3. **Keep your server updated** - run `sudo apt update && sudo apt upgrade` regularly
4. **Monitor logs regularly** for suspicious activity
5. **Backup your data** - automated backups run daily at 2 AM
6. **Test your backups** occasionally to ensure they work
7. **Rotate credentials** periodically for better security

## 📞 Emergency Contacts

- **Server Issues**: Check system logs with `sudo journalctl -xe`
- **Bot Issues**: Check bot logs with `sudo journalctl -u football-bot -f`
- **Database Issues**: Check PostgreSQL logs with `sudo tail -f /var/log/postgresql/postgresql-*.log`

## 🎯 Production Checklist

Before going live, ensure:

- [ ] All sensitive data is removed from code
- [ ] Environment variables are properly configured
- [ ] Database is secure and backed up
- [ ] Firewall is properly configured
- [ ] Bot service is running and enabled
- [ ] Monitoring is active
- [ ] Backups are working
- [ ] SSL certificates are installed (if using webhooks)
- [ ] Domain is pointed to server (if applicable)
- [ ] Bot is responding correctly to all commands

---

**🎉 Your bot is now ready for production with enterprise-level security!**
