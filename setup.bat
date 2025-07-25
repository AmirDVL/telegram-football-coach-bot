@echo off
echo Installing Football Coach Telegram Bot...
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
python -m venv venv

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install requirements
echo Installing requirements...
pip install -r requirements.txt

:: Check if .env file exists
if not exist .env (
    echo.
    echo Warning: .env file not found!
    echo Please create .env file with your bot token:
    echo BOT_TOKEN=your_bot_token_here
    echo ADMIN_ID=your_admin_chat_id_here
    echo.
)

echo.
echo Installation complete!
echo.
echo To run the bot:
echo 1. Add your bot token to .env file
echo 2. Run: python main.py
echo.
pause
