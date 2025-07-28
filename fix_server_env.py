#!/usr/bin/env python3
"""
Fix Server .env File
This script ensures the .env file has the correct ADMIN_IDS configuration
"""

import os
import shutil

def fix_server_env():
    """Fix the server's .env file"""
    
    print("🔧 Fixing server .env file...")
    
    env_content = """# Telegram Bot Configuration
BOT_TOKEN=8212660543:AAHS3mM8IxzgLFRqwbzgiX8H76HUgMe52OM
ADMIN_ID=293893885
ADMIN_IDS=427694849,6451449152,293893885

# Database Configuration (USE SECURE CREDENTIALS FROM STEP 4.5)
USE_DATABASE=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_coach_bot
DB_USER=footballbot_app
DB_PASSWORD=SecureBot123!

# Production Settings
DEBUG=true
# Security Settings
MAX_REQUESTS_PER_MINUTE=60
RATE_LIMIT_ENABLED=true
LOG_LEVEL=INFO
"""

    # Backup existing .env if it exists
    if os.path.exists('.env'):
        print("📁 Backing up existing .env file...")
        shutil.copy('.env', '.env.backup')
        print("✅ Backup created: .env.backup")
    
    # Write new .env file
    print("✍️  Writing new .env file...")
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ .env file updated successfully!")
    
    # Verify the fix
    print("🔍 Verifying .env file...")
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'ADMIN_IDS=427694849,6451449152,293893885' in content:
        print("✅ ADMIN_IDS correctly set!")
    else:
        print("❌ ADMIN_IDS not found in file!")
    
    # Test loading
    print("🧪 Testing environment loading...")
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)  # Force reload
        
        admin_ids_value = os.getenv('ADMIN_IDS')
        print(f"📋 ADMIN_IDS value: {repr(admin_ids_value)}")
        
        if admin_ids_value:
            print("🎉 Environment loading successful!")
        else:
            print("❌ ADMIN_IDS still not loading")
            
    except Exception as e:
        print(f"❌ Error testing: {e}")

if __name__ == "__main__":
    fix_server_env()
