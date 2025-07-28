#!/bin/bash

echo "Starting Football Coach Telegram Bot..."
echo ""

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup.sh first."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo ".env file not found!"
    echo "Please create .env file with your bot token:"
    echo "BOT_TOKEN=your_bot_token_here"
    echo "ADMIN_ID=your_admin_chat_id_here"
    exit 1
fi

source venv/bin/activate
python main.py
