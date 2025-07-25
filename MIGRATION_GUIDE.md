# 🚚 Migration Guide: Shared Host → VPS

## 📋 **When to Migrate**

### **Performance Indicators:**
- Bot response time > 3 seconds
- Memory usage consistently > 80%
- Host kills bot processes frequently
- User complaints about timeouts
- Need for advanced features (databases, etc.)

### **User Volume Thresholds:**
- **50+ concurrent users:** Consider migration
- **100+ concurrent users:** Migrate immediately
- **500+ total users:** Definitely need VPS

---

## 🎯 **Best VPS Providers for Your Bot**

### **🏆 Recommended: Hetzner Cloud**
```
Plan: CX21
- 2 vCPU
- 4GB RAM
- 40GB SSD
- 20TB traffic
Price: €4.15/month (~$4.50)
```

### **🥈 Alternative: DigitalOcean**
```
Plan: Basic Droplet
- 2 vCPU
- 2GB RAM
- 50GB SSD
- 2TB transfer
Price: $12/month
```

### **🥉 Budget Option: Vultr**
```
Plan: Regular Performance
- 1 vCPU
- 2GB RAM
- 55GB SSD
- 2TB bandwidth
Price: $10/month
```

---

## 🔧 **Migration Process**

### **Step 1: Prepare VPS**

```bash
# 1. Create VPS (Ubuntu 22.04 LTS)
# 2. SSH into VPS
ssh root@your-vps-ip

# 3. Update system
apt update && apt upgrade -y

# 4. Install Python 3.12
apt install python3.12 python3.12-venv python3.12-pip -y

# 5. Create bot user
adduser botuser
usermod -aG sudo botuser

# 6. Setup firewall
ufw allow ssh
ufw allow 443
ufw --force enable
```

### **Step 2: Transfer Bot Files**

```bash
# From your local machine/shared host
scp -r telegram_bot/ botuser@your-vps-ip:/home/botuser/

# OR use git
ssh botuser@your-vps-ip
git clone https://github.com/yourusername/telegram-bot.git
cd telegram-bot
```

### **Step 3: Setup Bot on VPS**

```bash
# SSH to VPS as botuser
ssh botuser@your-vps-ip
cd telegram_bot

# Run the deployment script
chmod +x deploy_vps.sh
./deploy_vps.sh
```

### **Step 4: Setup SystemD Service**

```bash
# Create service file
sudo nano /etc/systemd/system/football-bot.service
```

```ini
[Unit]
Description=Football Coach Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/telegram_bot
ExecStart=/home/botuser/telegram_bot/venv/bin/python main.py
Restart=always
RestartSec=10

Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable football-bot
sudo systemctl start football-bot

# Check status
sudo systemctl status football-bot
```

---

## 📊 **Data Migration**

### **Backup Current Data**

```bash
# On shared host
tar -czf bot_backup_$(date +%Y%m%d).tar.gz \
    user_data.json \
    payments.json \
    questionnaire_data.json \
    admin_data.json \
    statistics.json
```

### **Transfer to VPS**

```bash
# Upload backup
scp bot_backup_*.tar.gz botuser@your-vps-ip:/home/botuser/telegram_bot/

# On VPS, extract backup
cd /home/botuser/telegram_bot
tar -xzf bot_backup_*.tar.gz
```

---

## 🛡️ **VPS Security Setup**

### **1. SSH Security**

```bash
# Disable password auth, use keys only
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no

sudo systemctl restart ssh
```

### **2. Install Fail2Ban**

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### **3. Setup SSL (Optional - for webhooks)**

```bash
# Install certbot
sudo apt install certbot -y

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com
```

---

## 🔄 **Zero-Downtime Migration**

### **Method 1: DNS Switch**
1. Set up bot on VPS
2. Test thoroughly
3. Update webhook URL to VPS
4. Stop bot on shared host

### **Method 2: Gradual Migration**
1. Run both bots temporarily
2. Route new users to VPS
3. Migrate existing users gradually
4. Shut down shared host bot

---

## 📈 **Performance Optimization on VPS**

### **1. Database Migration**

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Setup database
sudo -u postgres createdb football_bot
sudo -u postgres createuser botuser
sudo -u postgres psql -c "ALTER USER botuser WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE football_bot TO botuser;"
```

### **2. Redis for Caching**

```bash
# Install Redis
sudo apt install redis-server -y
sudo systemctl enable redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Uncomment: bind 127.0.0.1
# Set: maxmemory 256mb
# Set: maxmemory-policy allkeys-lru

sudo systemctl restart redis-server
```

### **3. Monitoring Setup**

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs -y

# Setup log rotation
sudo nano /etc/logrotate.d/football-bot
```

```
/home/botuser/telegram_bot/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 botuser botuser
}
```

---

## 💰 **Cost Comparison**

### **Shared Host:**
- Monthly: $0 (using existing)
- Setup time: 30 minutes
- Maintenance: Low
- Scalability: Limited

### **VPS (Hetzner):**
- Monthly: €4.15 (~$4.50)
- Setup time: 2 hours
- Maintenance: Medium
- Scalability: High

### **VPS (DigitalOcean):**
- Monthly: $12
- Setup time: 1 hour (better docs)
- Maintenance: Medium
- Scalability: High

---

## 🎯 **Migration Decision Matrix**

| Factor | Shared Host | VPS |
|--------|-------------|-----|
| Cost | Free | $5-12/month |
| Performance | Limited | Excellent |
| Control | Minimal | Full |
| Scalability | Poor | Excellent |
| Reliability | Depends on host | High |
| Security | Basic | Configurable |
| Learning curve | Low | Medium |

---

## 📞 **Support During Migration**

If you need help with migration:

1. **Test VPS setup** first with free trials
2. **Keep shared host running** during migration
3. **Monitor both** for 48 hours
4. **Gradual user migration** if possible

Would you like me to create the VPS deployment script as well?
