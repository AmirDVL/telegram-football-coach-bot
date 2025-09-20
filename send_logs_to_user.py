#!/usr/bin/env python3
"""
Send log files to specific Telegram users via the bot
Usage: python send_logs_to_user.py <user_id> <log_file_path> [message]
"""

import sys
import os
import asyncio
import requests
from pathlib import Path

# Import bot configuration
try:
    from config import Config
except ImportError:
    print("❌ Error: config.py not found. Make sure you're in the bot directory.")
    sys.exit(1)

def send_document_via_telegram(bot_token, user_id, file_path, caption=None):
    """Send a document to a Telegram user using the bot token"""
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File {file_path} not found")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    
    try:
        with open(file_path, 'rb') as file:
            files = {'document': file}
            data = {
                'chat_id': user_id,
                'caption': caption or f"📄 Log file: {os.path.basename(file_path)}"
            }
            
            print(f"📤 Sending {os.path.basename(file_path)} to user {user_id}...")
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                print("✅ File sent successfully!")
                return True
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error sending file: {e}")
        return False

def send_message_via_telegram(bot_token, user_id, message):
    """Send a text message to a Telegram user"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        'chat_id': user_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, data=data, timeout=30)
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Error sending message: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_recent_users():
    """Get list of recent users from logs for easy selection"""
    user_log_path = "logs/user_interactions.log"
    users = {}
    
    if os.path.exists(user_log_path):
        try:
            with open(user_log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-50:]  # Last 50 interactions
                
            for line in lines:
                if "USER:" in line:
                    # Extract user ID and username from log format
                    # Format: USER:123456789(@username) - action
                    try:
                        user_part = line.split("USER:")[1].split(" - ")[0]
                        user_id = user_part.split("(")[0]
                        username = user_part.split("(@")[1].split(")")[0] if "(@" in user_part else "unknown"
                        users[user_id] = username
                    except:
                        continue
                        
        except Exception as e:
            print(f"⚠️ Warning: Could not read user logs: {e}")
    
    return users

def main():
    if len(sys.argv) < 3:
        print("📋 Usage: python send_logs_to_user.py <user_id> <log_file_path> [message]")
        print("\n🔍 Recent users from logs:")
        
        users = get_recent_users()
        if users:
            for uid, username in list(users.items())[-10:]:  # Show last 10 users
                print(f"   {uid} (@{username})")
        else:
            print("   No recent users found in logs")
            
        print(f"\n📁 Available log files:")
        log_files = list(Path("logs").glob("*.log")) + list(Path(".").glob("*logs*.txt"))
        for log_file in log_files:
            print(f"   {log_file}")
            
        print(f"\n💡 Example:")
        print(f"   python send_logs_to_user.py 293893885 august_14_logs.txt")
        print(f"   python send_logs_to_user.py 293893885 logs/user_interactions.log 'Debug logs'")
        return
    
    user_id = sys.argv[1]
    file_path = sys.argv[2]
    custom_message = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Check if bot token is available
    if not Config.BOT_TOKEN:
        print("❌ Error: BOT_TOKEN not found in environment variables!")
        print("Make sure your .env file contains BOT_TOKEN=your_bot_token")
        return
    
    # Create caption with file info
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    caption = f"📄 <b>{os.path.basename(file_path)}</b>\n"
    caption += f"📊 Size: {file_size:,} bytes\n"
    caption += f"🕐 Generated: {Path(file_path).stat().st_mtime if os.path.exists(file_path) else 'unknown'}\n"
    
    if custom_message:
        caption += f"\n💬 {custom_message}"
    
    # Send the file
    success = send_document_via_telegram(Config.BOT_TOKEN, user_id, file_path, caption)
    
    if success:
        print(f"✅ Successfully sent {os.path.basename(file_path)} to user {user_id}")
    else:
        print(f"❌ Failed to send file to user {user_id}")

if __name__ == "__main__":
    main()
