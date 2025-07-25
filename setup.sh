#!/bin/bash

echo "Installing Football Coach Telegram Bot..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f .env ]; then
    echo ""
    echo "Warning: .env file not found!"
    echo "Please create .env file with your bot token:"
    echo "BOT_TOKEN=your_bot_token_here"
    echo "ADMIN_ID=your_admin_chat_id_here"
    echo ""
fi

echo ""
echo "Installation complete!"
echo ""
echo "To run the bot:"
echo "1. Add your bot token to .env file"
echo "2. Run: python main.py"
echo ""
