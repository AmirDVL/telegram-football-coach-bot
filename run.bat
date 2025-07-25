@echo off
echo Starting Football Coach Telegram Bot...
echo.

if not exist venv (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

if not exist .env (
    echo .env file not found! 
    echo Please create .env file with your bot token:
    echo BOT_TOKEN=your_bot_token_here
    echo ADMIN_ID=your_admin_chat_id_here
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python main.py

pause
