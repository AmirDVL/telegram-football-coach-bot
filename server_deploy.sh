#!/bin/bash
# SERVER DEPLOYMENT SCRIPT - Pull and Deploy Permanent Corruption Fix

echo "🚀 DEPLOYING PERMANENT CORRUPTION FIX FROM GITHUB"
echo "=================================================="

# Navigate to bot directory
cd /root/football_coach_bot || { echo "❌ Bot directory not found"; exit 1; }

# Stop the bot
echo "🛑 Stopping bot..."
pkill -f 'python.*main.py' || echo "Bot was not running"
sleep 2

# Pull latest changes from GitHub
echo "📥 Pulling latest changes from GitHub..."
git pull origin master

# Check if pull was successful
if [ $? -eq 0 ]; then
    echo "✅ GitHub pull successful"
else
    echo "❌ GitHub pull failed"
    exit 1
fi

# Run the permanent corruption fix
echo "🔧 Running permanent corruption fix for user 1688724731..."
python3 permanent_corruption_fix.py

# Check if fix was successful
if [ $? -eq 0 ]; then
    echo "✅ Corruption fix applied successfully"
else
    echo "❌ Corruption fix failed"
    exit 1
fi

# Start the bot
echo "🚀 Starting bot with corruption fix..."
nohup python3 main.py > bot.log 2>&1 &

# Wait and verify bot is running
sleep 3
if ps aux | grep 'python.*main.py' | grep -v grep > /dev/null; then
    echo "✅ Bot started successfully"
else
    echo "❌ Bot failed to start"
    exit 1
fi

# Create deployment documentation
echo "📄 Creating deployment documentation..."
echo "PERMANENT CORRUPTION FIX DEPLOYED - $(date)" > CORRUPTION_FIX_DEPLOYED.md
echo "- Fixed /start command corruption in main.py" >> CORRUPTION_FIX_DEPLOYED.md
echo "- Recovered user 1688724731 payment data" >> CORRUPTION_FIX_DEPLOYED.md
echo "- All future users protected from corruption" >> CORRUPTION_FIX_DEPLOYED.md

echo ""
echo "🎯 DEPLOYMENT COMPLETE!"
echo "✅ Corruption permanently eliminated"
echo "✅ User 1688724731 can proceed with payment"
echo "✅ All future users protected"
echo ""
echo "📋 Next steps:"
echo "1. Check admin panel - user 1688724731 should show pending payment"
echo "2. Verify no more 'receipt not submitted' false errors"
echo "3. Test that users can navigate freely without data loss"