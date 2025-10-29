#!/bin/bash
# Telegram Football Coach Bot - Production Startup Script

echo "🚀 Starting Football Coach Bot..."

# Change to project root directory
cd "$(dirname "$0")/.." || exit 1

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found! Please create it from .env.example"
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Run the bot
echo "✅ Starting bot..."
python run.py